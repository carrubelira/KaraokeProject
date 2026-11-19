//! The player's socket to the server, on its own thread: it reconnects on its own, hands every
//! message to the control thread with the instant it arrived, and sends what it is given.

use std::io::ErrorKind;
use std::sync::mpsc::{Receiver, Sender, TryRecvError};
use std::thread;
use std::time::Duration;

use kp_net::tungstenite::{self, Message, stream::MaybeTlsStream};
use kp_net::{Server, Socket};
use kp_proto::{PlayerMessage, ServerMessage};

pub enum Event {
    Connected,
    Disconnected(String),
    Message(ServerMessage, i64),
}

fn set_timeout(socket: &mut Socket) {
    let timeout = Some(Duration::from_millis(50));
    match socket.get_mut() {
        MaybeTlsStream::Plain(stream) => {
            let _ = stream.set_read_timeout(timeout);
        }
        MaybeTlsStream::Rustls(stream) => {
            let _ = stream.sock.set_read_timeout(timeout);
        }
        _ => {}
    }
}

/// Runs until `outgoing` is closed.
pub fn spawn(
    server: Server,
    events: Sender<Event>,
    outgoing: Receiver<PlayerMessage>,
) -> thread::JoinHandle<()> {
    thread::Builder::new()
        .name("server link".into())
        .spawn(move || {
            let mut backoff = Duration::from_millis(500);
            loop {
                let mut socket = match server.connect_socket("/api/players/ws") {
                    Ok(socket) => socket,
                    Err(error) => {
                        let _ = events.send(Event::Disconnected(error.to_string()));
                        thread::sleep(backoff);
                        backoff = (backoff * 2).min(Duration::from_secs(10));
                        if matches!(outgoing.try_recv(), Err(TryRecvError::Disconnected)) {
                            return;
                        }
                        continue;
                    }
                };
                backoff = Duration::from_millis(500);
                set_timeout(&mut socket);
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

/// Ok when the player is shutting down; Err with why the connection dropped.
fn pump(
    socket: &mut Socket,
    events: &Sender<Event>,
    outgoing: &Receiver<PlayerMessage>,
) -> Result<(), String> {
    loop {
        loop {
            match outgoing.try_recv() {
                Ok(message) => {
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
                        if events.send(Event::Message(message, received)).is_err() {
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
