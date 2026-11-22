//! kp-audio's socket to its server, on its own thread: it reconnects on its own, hands every
//! message to the control thread with the instant it arrived, and sends what it is given.
//!
//! The server is on this machine (decision 011): a plain WebSocket to the loopback, with the
//! secret the server made at this start (`KARAOKE_AUDIO_TOKEN`) in a header, never in the
//! address (which the server's access log writes down).

use std::io::ErrorKind;
use std::net::TcpStream;
use std::sync::mpsc::{Receiver, Sender, TryRecvError};
use std::thread;
use std::time::Duration;

use kp_proto::{AudioMessage, ServerMessage};
use tungstenite::client::IntoClientRequest;
use tungstenite::stream::MaybeTlsStream;
use tungstenite::{Message, WebSocket};

type Socket = WebSocket<MaybeTlsStream<TcpStream>>;

pub enum Event {
    Connected,
    Disconnected(String),
    Message(Box<ServerMessage>, i64),
}

/// `http://127.0.0.1:8765` → `ws://127.0.0.1:8765/api/audio/ws`.
pub fn socket_url(server: &str) -> String {
    let base = server.trim_end_matches('/');
    let base = base
        .strip_prefix("http://")
        .map(|rest| format!("ws://{rest}"))
        .unwrap_or_else(|| base.to_string());
    format!("{base}/api/audio/ws")
}

fn connect(url: &str, token: &str) -> Result<Socket, String> {
    let mut request = url.into_client_request().map_err(|e| e.to_string())?;
    let bearer = format!("Bearer {token}")
        .parse()
        .map_err(|_| "a token that is not ASCII")?;
    request.headers_mut().insert("Authorization", bearer);
    let (socket, _) = tungstenite::connect(request).map_err(|e| e.to_string())?;
    if let MaybeTlsStream::Plain(stream) = socket.get_ref() {
        let _ = stream.set_read_timeout(Some(Duration::from_millis(5)));
        let _ = stream.set_nodelay(true);
    }
    Ok(socket)
}

/// Runs until `outgoing` is closed.
pub fn spawn(
    url: String,
    token: String,
    events: Sender<Event>,
    outgoing: Receiver<AudioMessage>,
) -> thread::JoinHandle<()> {
    thread::Builder::new()
        .name("server link".into())
        .spawn(move || {
            let mut backoff = Duration::from_millis(200);
            loop {
                let mut socket = match connect(&url, &token) {
                    Ok(socket) => socket,
                    Err(error) => {
                        let _ = events.send(Event::Disconnected(error));
                        thread::sleep(backoff);
                        backoff = (backoff * 2).min(Duration::from_secs(5));
                        if matches!(outgoing.try_recv(), Err(TryRecvError::Disconnected)) {
                            return;
                        }
                        continue;
                    }
                };
                backoff = Duration::from_millis(200);
                let _ = events.send(Event::Connected);
                let reason = pump(&mut socket, &events, &outgoing);
                let _ = socket.close(None);
                match reason {
                    Ok(()) => return,
                    Err(error) => {
                        let _ = events.send(Event::Disconnected(error));
                    }
                }
            }
        })
        .expect("the link thread starts")
}

/// Ok when kp-audio is shutting down; Err with why the connection dropped.
fn pump(
    socket: &mut Socket,
    events: &Sender<Event>,
    outgoing: &Receiver<AudioMessage>,
) -> Result<(), String> {
    loop {
        loop {
            match outgoing.try_recv() {
                Ok(mut message) => {
                    // Stamped as it leaves, not when it was queued: the wait for the socket would
                    // count as network time and skew the offset learnt from the answer.
                    if let AudioMessage::TimeRequest { sent } = &mut message {
                        *sent = crate::clock::now_us();
                    }
                    let text = serde_json::to_string(&message).expect("serialisable");
                    socket.send(Message::text(text)).map_err(|e| e.to_string())?;
                }
                Err(TryRecvError::Empty) => break,
                Err(TryRecvError::Disconnected) => return Ok(()),
            }
        }
        match socket.read() {
            Ok(Message::Text(text)) => {
                let received = crate::clock::now_us();
                match serde_json::from_str::<ServerMessage>(&text) {
                    Ok(message) => {
                        if events.send(Event::Message(Box::new(message), received)).is_err() {
                            return Ok(());
                        }
                    }
                    Err(error) => log::warn!("unknown message from the server: {error}"),
                }
            }
            Ok(Message::Close(_)) => return Err("the server closed the connection".into()),
            Ok(_) => {}
            Err(tungstenite::Error::Io(error))
                if matches!(error.kind(), ErrorKind::WouldBlock | ErrorKind::TimedOut) => {}
            Err(error) => return Err(error.to_string()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_socket_url_comes_from_the_server_url() {
        assert_eq!(
            socket_url("http://127.0.0.1:8765/"),
            "ws://127.0.0.1:8765/api/audio/ws"
        );
    }
}
