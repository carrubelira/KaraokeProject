//! HTTPS and WebSocket to the server, trusting exactly one certificate (plan v4 §3).
//!
//! The server's certificate is self-signed; the player pins its SHA-256 when it enrols
//! ([`enrol`]) and from then on accepts that certificate and no other, whatever name or address
//! the server is reached at. Plain `http://` works too, for development.

use std::io::Read;
use std::net::TcpStream;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use kp_proto::{Enrolled, Enrollment};
use rustls::client::danger::{HandshakeSignatureValid, ServerCertVerified, ServerCertVerifier};
use rustls::pki_types::{CertificateDer, ServerName, UnixTime};
use rustls::{DigitallySignedStruct, SignatureScheme};
use sha2::{Digest, Sha256};

pub use tungstenite;

#[derive(Debug, thiserror::Error)]
pub enum NetError {
    #[error("the server presents certificate {seen}, not the pinned {expected}")]
    Fingerprint { seen: String, expected: String },
    #[error("HTTP {status}: {body}")]
    Status { status: u16, body: String },
    #[error("{0}")]
    Transport(String),
    #[error("bad answer: {0}")]
    Decode(String),
}

impl From<ureq::Error> for NetError {
    fn from(error: ureq::Error) -> Self {
        match error {
            ureq::Error::Status(status, response) => {
                let body = response.into_string().unwrap_or_default();
                if body.contains("certificate") {
                    Self::Transport(body)
                } else {
                    Self::Status { status, body }
                }
            }
            ureq::Error::Transport(transport) => {
                let text = transport.to_string();
                if let Some(seen) = text.split("FINGERPRINT:").nth(1) {
                    return Self::Fingerprint {
                        seen: seen.chars().take(64).collect(),
                        expected: String::new(),
                    };
                }
                Self::Transport(text)
            }
        }
    }
}

/// Lower-case hex SHA-256 of a certificate in DER.
pub fn fingerprint(der: &[u8]) -> String {
    hex::encode(Sha256::digest(der))
}

/// Accepts only the certificate whose SHA-256 is `expected` (or, with `None`, any one, recording
/// it: trust on first use). Signatures are still checked against that certificate's key.
#[derive(Debug)]
pub struct PinnedVerifier {
    expected: Option<String>,
    seen: Mutex<Option<String>>,
    provider: Arc<rustls::crypto::CryptoProvider>,
}

impl PinnedVerifier {
    pub fn new(expected: Option<&str>) -> Arc<Self> {
        Arc::new(Self {
            expected: expected.map(|e| e.to_lowercase().replace(':', "")),
            seen: Mutex::new(None),
            provider: Arc::new(rustls::crypto::ring::default_provider()),
        })
    }

    pub fn seen(&self) -> Option<String> {
        self.seen.lock().ok().and_then(|seen| seen.clone())
    }
}

impl ServerCertVerifier for PinnedVerifier {
    fn verify_server_cert(
        &self,
        end_entity: &CertificateDer<'_>,
        _intermediates: &[CertificateDer<'_>],
        _server_name: &ServerName<'_>,
        _ocsp: &[u8],
        _now: UnixTime,
    ) -> Result<ServerCertVerified, rustls::Error> {
        let seen = fingerprint(end_entity.as_ref());
        if let Ok(mut slot) = self.seen.lock() {
            *slot = Some(seen.clone());
        }
        match &self.expected {
            Some(expected) if *expected != seen => Err(rustls::Error::General(format!("FINGERPRINT:{seen}"))),
            _ => Ok(ServerCertVerified::assertion()),
        }
    }

    fn verify_tls12_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls12_signature(
            message,
            cert,
            dss,
            &self.provider.signature_verification_algorithms,
        )
    }

    fn verify_tls13_signature(
        &self,
        message: &[u8],
        cert: &CertificateDer<'_>,
        dss: &DigitallySignedStruct,
    ) -> Result<HandshakeSignatureValid, rustls::Error> {
        rustls::crypto::verify_tls13_signature(
            message,
            cert,
            dss,
            &self.provider.signature_verification_algorithms,
        )
    }

    fn supported_verify_schemes(&self) -> Vec<SignatureScheme> {
        self.provider
            .signature_verification_algorithms
            .supported_schemes()
    }
}

pub fn tls_config(verifier: Arc<PinnedVerifier>) -> Arc<rustls::ClientConfig> {
    let provider = Arc::new(rustls::crypto::ring::default_provider());
    let config = rustls::ClientConfig::builder_with_provider(provider)
        .with_safe_default_protocol_versions()
        .expect("ring supports the default protocol versions")
        .dangerous()
        .with_custom_certificate_verifier(verifier)
        .with_no_client_auth();
    Arc::new(config)
}

/// A client for one server, with the node's credential.
#[derive(Clone)]
pub struct Server {
    base: String,
    credential: Option<String>,
    agent: ureq::Agent,
    tls: Option<Arc<rustls::ClientConfig>>,
}

impl Server {
    pub fn new(base: &str, credential: Option<&str>, fingerprint: Option<&str>) -> Self {
        let base = base.trim_end_matches('/').to_string();
        let mut builder = ureq::AgentBuilder::new()
            .timeout_connect(Duration::from_secs(10))
            .timeout_read(Duration::from_secs(60));
        let mut tls = None;
        if base.starts_with("https://") {
            let config = tls_config(PinnedVerifier::new(fingerprint));
            builder = builder.tls_config(config.clone());
            tls = Some(config);
        }
        Self {
            base,
            credential: credential.map(str::to_string),
            agent: builder.build(),
            tls,
        }
    }

    pub fn base(&self) -> &str {
        &self.base
    }

    fn request(&self, method: &str, path: &str) -> ureq::Request {
        let request = self.agent.request(method, &format!("{}{path}", self.base));
        match &self.credential {
            Some(credential) => request.set("Authorization", &format!("Bearer {credential}")),
            None => request,
        }
    }

    pub fn get_json<T: serde::de::DeserializeOwned>(&self, path: &str) -> Result<T, NetError> {
        let response = self.request("GET", path).call()?;
        response.into_json().map_err(|e| NetError::Decode(e.to_string()))
    }

    pub fn post_json<B: serde::Serialize, T: serde::de::DeserializeOwned>(
        &self,
        path: &str,
        body: &B,
    ) -> Result<T, NetError> {
        let response = self.request("POST", path).send_json(body)?;
        response.into_json().map_err(|e| NetError::Decode(e.to_string()))
    }

    /// Reads a blob from `offset` on, handing each chunk to `sink`; returns the bytes read.
    pub fn get_blob(
        &self,
        sha256: &str,
        offset: u64,
        mut sink: impl FnMut(&[u8]) -> std::io::Result<()>,
    ) -> Result<(u64, bool), NetError> {
        let mut request = self.request("GET", &format!("/api/blobs/{sha256}"));
        if offset > 0 {
            request = request.set("Range", &format!("bytes={offset}-"));
        }
        let response = request.call()?;
        let partial = response.status() == 206;
        let mut reader = response.into_reader();
        let mut buffer = vec![0u8; 1 << 16];
        let mut total = 0u64;
        loop {
            let n = reader
                .read(&mut buffer)
                .map_err(|e| NetError::Transport(e.to_string()))?;
            if n == 0 {
                break;
            }
            sink(&buffer[..n]).map_err(|e| NetError::Transport(e.to_string()))?;
            total += n as u64;
        }
        Ok((total, partial))
    }

    /// The server's blob path, for a player on the server's own machine.
    pub fn local_path(&self, sha256: &str) -> Option<String> {
        #[derive(serde::Deserialize)]
        struct Local {
            path: String,
        }
        self.get_json::<Local>(&format!("/api/blobs/{sha256}/local"))
            .ok()
            .map(|l| l.path)
    }

    /// Opens the player's WebSocket.
    pub fn connect_socket(&self, path: &str) -> Result<Socket, NetError> {
        use tungstenite::client::IntoClientRequest;

        let url = format!("{}{path}", self.base.replacen("http", "ws", 1));
        let mut request = url
            .as_str()
            .into_client_request()
            .map_err(|e| NetError::Transport(e.to_string()))?;
        if let Some(credential) = &self.credential {
            let value = format!("Bearer {credential}")
                .parse()
                .map_err(|_| NetError::Transport("bad credential".into()))?;
            request.headers_mut().insert("Authorization", value);
        }
        let uri = request.uri().clone();
        let host = uri
            .host()
            .unwrap_or("localhost")
            .trim_matches(['[', ']'])
            .to_string();
        let port = uri
            .port_u16()
            .unwrap_or(if self.tls.is_some() { 443 } else { 80 });
        let stream =
            TcpStream::connect((host.as_str(), port)).map_err(|e| NetError::Transport(e.to_string()))?;
        stream.set_nodelay(true).ok();
        let connector = match &self.tls {
            Some(config) => tungstenite::Connector::Rustls(config.clone()),
            None => tungstenite::Connector::Plain,
        };
        let (socket, _) = tungstenite::client_tls_with_config(request, stream, None, Some(connector))
            .map_err(|e| NetError::Transport(e.to_string()))?;
        Ok(socket)
    }
}

pub type Socket = tungstenite::WebSocket<tungstenite::stream::MaybeTlsStream<TcpStream>>;

/// Enrols with a one-time token. With `fingerprint`, the server must present that certificate;
/// without it, the one it presents is trusted from now on (and returned, to show the operator).
pub fn enrol(
    base: &str,
    request: &Enrollment,
    fingerprint: Option<&str>,
) -> Result<(Enrolled, Option<String>), NetError> {
    let verifier = PinnedVerifier::new(fingerprint);
    let mut builder = ureq::AgentBuilder::new().timeout(Duration::from_secs(30));
    if base.starts_with("https://") {
        builder = builder.tls_config(tls_config(verifier.clone()));
    }
    let agent = builder.build();
    let url = format!("{}/api/nodes/enroll", base.trim_end_matches('/'));
    let response = agent.post(&url).send_json(request).map_err(|error| {
        let error = NetError::from(error);
        match (error, fingerprint) {
            (NetError::Fingerprint { seen, .. }, Some(expected)) => NetError::Fingerprint {
                seen,
                expected: expected.into(),
            },
            (error, _) => error,
        }
    })?;
    let enrolled: Enrolled = response
        .into_json()
        .map_err(|e| NetError::Decode(e.to_string()))?;
    Ok((enrolled, verifier.seen()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fingerprint_is_sha256_hex() {
        assert_eq!(
            fingerprint(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn pinned_verifier_accepts_only_its_certificate() {
        let der = CertificateDer::from(b"not really a certificate".to_vec());
        let good = fingerprint(der.as_ref());
        let name = ServerName::try_from("localhost").unwrap();
        let pinned = PinnedVerifier::new(Some(&good.to_uppercase()));
        assert!(
            pinned
                .verify_server_cert(&der, &[], &name, &[], UnixTime::now())
                .is_ok()
        );
        let other = PinnedVerifier::new(Some(&"0".repeat(64)));
        let refused = other.verify_server_cert(&der, &[], &name, &[], UnixTime::now());
        assert!(refused.is_err());
        assert_eq!(other.seen(), Some(good));
        let first_use = PinnedVerifier::new(None);
        assert!(
            first_use
                .verify_server_cert(&der, &[], &name, &[], UnixTime::now())
                .is_ok()
        );
    }
}
