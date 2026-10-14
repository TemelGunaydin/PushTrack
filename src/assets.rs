//! Explicit, checksum-pinned model installation. Never contacts the network during scans.
use crate::process;
use anyhow::{Context, Result, ensure};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    os::unix::fs::MetadataExt,
    path::{Path, PathBuf},
    process::Command,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    thread,
    time::{Duration, Instant},
};

// All11 v2 assets reconciled against native checksums; public prerelease verified.
pub const RELEASE_PUBLISHED: bool = true;
#[derive(Clone, Debug, Deserialize)]
pub struct Asset {
    pub name: String,
    pub bytes: u64,
    pub sha256: String,
}
#[derive(Clone, Debug, Deserialize)]
pub struct ModelSpec {
    pub id: String,
    pub name: String,
    pub filename: String,
    pub bytes: u64,
    pub sha256: String,
    pub license: String,
    pub publisher: String,
    pub release_tag: String,
    pub repository: String,
    pub parts: Vec<Asset>,
    pub notices: Vec<Asset>,
}
pub fn catalogue() -> ModelSpec {
    serde_json::from_str(include_str!("../assets/models/qwen35-4b-q4km-v2.json"))
        .expect("Built-in model catalogue")
}
fn cache_root() -> Result<PathBuf> {
    let base = std::env::var_os("XDG_CACHE_HOME")
        .map(PathBuf::from)
        .filter(|path| path.is_absolute());
    let base = match base {
        Some(path) => path,
        None => PathBuf::from(
            std::env::var_os("HOME").context("HOME is not set; set absolute XDG_CACHE_HOME")?,
        )
        .join(".cache"),
    };
    Ok(base)
}
pub fn model_directory() -> Result<PathBuf> {
    Ok(cache_root()?.join("pushtrack/models").join(catalogue().id))
}
pub(crate) fn cached_runtime_path() -> Result<Option<PathBuf>> {
    #[cfg(all(target_os = "macos", target_arch = "aarch64"))]
    {
        Ok(Some(cache_root()?.join(
            "pushtrack/runtimes/llama-b11429-macos-arm64-0001/llama-b11429/llama-server",
        )))
    }
    #[cfg(not(all(target_os = "macos", target_arch = "aarch64")))]
    {
        Ok(None)
    }
}
pub fn model_path() -> Result<PathBuf> {
    Ok(model_directory()?.join(catalogue().filename))
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Phase {
    Downloading,
    Verifying,
    Assembling,
}
#[derive(Clone, Debug)]
pub struct Progress {
    pub phase: Phase,
    pub label: String,
    pub bytes: u64,
    pub total: u64,
    pub bytes_per_second: f64,
}
pub enum Update {
    Progress(Progress),
    Ready(PathBuf),
    Failed(String),
}

fn regular(path: &Path) -> Result<Option<u64>> {
    match fs::symlink_metadata(path) {
        Ok(meta) => {
            ensure!(
                meta.is_file() && meta.nlink() == 1,
                "Unsafe model-cache file; preserve and inspect {}",
                path.display()
            );
            Ok(Some(meta.len()))
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.into()),
    }
}
fn check_cancel(cancel: &AtomicBool) -> Result<()> {
    ensure!(
        !cancel.load(Ordering::Relaxed),
        "Cancelled; partial downloads preserved"
    );
    Ok(())
}
fn report(
    send: &mpsc::Sender<Update>,
    phase: Phase,
    label: &str,
    bytes: u64,
    total: u64,
    rate: f64,
) {
    let _ = send.send(Update::Progress(Progress {
        phase,
        label: label.into(),
        bytes,
        total,
        bytes_per_second: rate,
    }));
}
fn verify(
    path: &Path,
    expected: &Asset,
    cancel: &AtomicBool,
    send: &mpsc::Sender<Update>,
) -> Result<()> {
    ensure!(
        regular(path)? == Some(expected.bytes),
        "Model asset size mismatch; file preserved: {}",
        expected.name
    );
    let mut file = File::open(path)?;
    let mut digest = Sha256::new();
    let mut bytes = 0;
    let mut buffer = [0u8; 65536];
    let mut tick = Instant::now();
    report(
        send,
        Phase::Verifying,
        &expected.name,
        0,
        expected.bytes,
        0.,
    );
    loop {
        check_cancel(cancel)?;
        let count = file.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
        bytes += count as u64;
        if tick.elapsed() >= Duration::from_millis(100) {
            report(
                send,
                Phase::Verifying,
                &expected.name,
                bytes,
                expected.bytes,
                0.,
            );
            tick = Instant::now();
        }
    }
    ensure!(
        format!("{:x}", digest.finalize()) == expected.sha256,
        "Model asset SHA-256 mismatch; file preserved: {}",
        expected.name
    );
    report(
        send,
        Phase::Verifying,
        &expected.name,
        bytes,
        expected.bytes,
        0.,
    );
    Ok(())
}
fn valid_name(name: &str) -> bool {
    !name.is_empty()
        && !name.starts_with('.')
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'-' | b'_'))
}
fn validate(spec: &ModelSpec) -> Result<()> {
    ensure!(
        valid_name(&spec.id) && valid_name(&spec.filename) && valid_name(&spec.release_tag),
        "Invalid built-in asset identity"
    );
    ensure!(
        spec.repository == "TemelGunaydin/PushTrack" && !spec.parts.is_empty(),
        "Unsupported model repository/parts"
    );
    let mut names = std::collections::HashSet::new();
    for asset in spec.parts.iter().chain(&spec.notices) {
        ensure!(
            valid_name(&asset.name)
                && asset.bytes > 0
                && asset.sha256.len() == 64
                && asset.sha256.bytes().all(|byte| byte.is_ascii_hexdigit()),
            "Invalid pinned asset metadata"
        );
        ensure!(names.insert(&asset.name), "Duplicate asset name");
    }
    ensure!(
        spec.parts.iter().map(|asset| asset.bytes).sum::<u64>() == spec.bytes,
        "Incomplete model parts"
    );
    Ok(())
}
struct Lock(PathBuf);
impl Drop for Lock {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn download(
    directory: &Path,
    asset: &Asset,
    spec: &ModelSpec,
    curl: &Path,
    cancel: &AtomicBool,
    send: &mpsc::Sender<Update>,
) -> Result<PathBuf> {
    let final_path = directory.join(&asset.name);
    if regular(&final_path)?.is_some() {
        verify(&final_path, asset, cancel, send)?;
        return Ok(final_path);
    }
    let partial = directory.join(format!("{}.partial", asset.name));
    let offset = regular(&partial)?.unwrap_or(0);
    ensure!(
        offset <= asset.bytes,
        "Partial file exceeds pinned size; preserve and inspect"
    );
    if offset < asset.bytes {
        // Exclusive creation prevents accidental symlink/old-file truncation; curl only resumes this owned file.
        if offset == 0 && !partial.exists() {
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(&partial)?;
        }
        let url = format!(
            "https://github.com/{}/releases/download/{}/{}",
            spec.repository, spec.release_tag, asset.name
        );
        let headers = tempfile::NamedTempFile::new_in(directory)?;
        let mut command = Command::new(curl);
        command
            .args([
                "-q",
                "--fail",
                "--location",
                "--silent",
                "--show-error",
                "--proto",
                "=https",
                "--proto-redir",
                "=https",
                "--retry",
                "0",
                "--connect-timeout",
                "10",
                "--max-time",
                "3600",
                "--speed-time",
                "30",
                "--speed-limit",
                "1024",
                "--continue-at",
            ])
            .arg(offset.to_string())
            .arg("--dump-header")
            .arg(headers.path())
            .arg("--output")
            .arg(&partial)
            .arg("--url")
            .arg(url);
        // No auth, .curlrc, source text, retry loop, shell or endpoint selected by repository content.
        let start = Instant::now();
        let mut tick = Instant::now();
        let output = process::run_observed(
            command,
            None,
            cancel,
            (Duration::from_secs(3610), Some(8192)),
            "Model download",
            || {
                let size = regular(&partial)?.context("Download file disappeared")?;
                ensure!(
                    size >= offset && size <= asset.bytes,
                    "Model download changed/exceeded pinned size; partial preserved"
                );
                ensure!(
                    fs::metadata(headers.path())?.len() <= 131072,
                    "Download headers exceeded limit"
                );
                if tick.elapsed() >= Duration::from_millis(100) {
                    report(
                        send,
                        Phase::Downloading,
                        &asset.name,
                        size,
                        asset.bytes,
                        (size - offset) as f64 / start.elapsed().as_secs_f64().max(0.001),
                    );
                    tick = Instant::now();
                }
                Ok(())
            },
        )?;
        ensure!(
            output.status.success(),
            "Model download failed; partial preserved, no automatic retry: {}",
            output.stderr.trim()
        );
        let raw = fs::read(headers.path())?;
        ensure!(raw.len() <= 131072, "Download headers exceeded limit");
        let raw = String::from_utf8(raw)?;
        let last = raw
            .split("\r\n\r\n")
            .filter(|block| block.starts_with("HTTP/"))
            .last()
            .context("Missing final HTTP headers")?;
        let status = last
            .lines()
            .next()
            .unwrap_or("")
            .split_whitespace()
            .nth(1)
            .unwrap_or("");
        if offset > 0 {
            ensure!(
                status == "206",
                "Resume requires HTTP206; partial preserved"
            );
            let range = last
                .lines()
                .find_map(|line| {
                    line.split_once(':')
                        .filter(|(name, _)| name.eq_ignore_ascii_case("content-range"))
                        .map(|(_, value)| value.trim())
                })
                .context("Missing resume Content-Range")?;
            ensure!(
                range == format!("bytes {}-{}/{}", offset, asset.bytes - 1, asset.bytes),
                "Incorrect resume range; partial preserved"
            );
        } else {
            ensure!(
                status == "200" || status == "206",
                "Unexpected model response"
            );
        }
    }
    verify(&partial, asset, cancel, send)?;
    check_cancel(cancel)?;
    // Hard-link publication is atomic and cannot overwrite any existing file.
    fs::hard_link(&partial, &final_path)?;
    fs::remove_file(&partial)?;
    Ok(final_path)
}
fn install(
    spec: &ModelSpec,
    directory: &Path,
    curl: &Path,
    cancel: &AtomicBool,
    send: &mpsc::Sender<Update>,
) -> Result<PathBuf> {
    validate(spec)?;
    check_cancel(cancel)?;
    fs::create_dir_all(directory)?;
    let lock_path = directory.join(".download.lock");
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&lock_path)
        .context("Model installation is locked; inspect an earlier job before removing its lock")?;
    let _lock = Lock(lock_path);
    let model = Asset {
        name: spec.filename.clone(),
        bytes: spec.bytes,
        sha256: spec.sha256.clone(),
    };
    let path = directory.join(&model.name);
    if regular(&path)?.is_some() {
        verify(&path, &model, cancel, send)?;
        for asset in &spec.notices {
            download(directory, asset, spec, curl, cancel, send)?;
        }
        return Ok(path);
    }
    let disk = nix::sys::statvfs::statvfs(directory)?;
    ensure!(
        u128::from(disk.blocks_available()).saturating_mul(u128::from(disk.fragment_size()))
            >= u128::from(spec.bytes) * 2 + 2_000_000_000,
        "Insufficient disk reserve: allow 2x model size plus2GB; partials preserved"
    );
    let mut parts = vec![];
    for asset in &spec.parts {
        parts.push(download(directory, asset, spec, curl, cancel, send)?);
    }
    for asset in &spec.notices {
        download(directory, asset, spec, curl, cancel, send)?;
    }
    let mut temp = tempfile::NamedTempFile::new_in(directory)?;
    let mut done = 0;
    let mut buffer = [0u8; 65536];
    let mut tick = Instant::now();
    for part in parts {
        let mut file = File::open(part)?;
        loop {
            check_cancel(cancel)?;
            let count = file.read(&mut buffer)?;
            if count == 0 {
                break;
            }
            temp.write_all(&buffer[..count])?;
            done += count as u64;
            if tick.elapsed() >= Duration::from_millis(100) {
                report(
                    send,
                    Phase::Assembling,
                    &spec.filename,
                    done,
                    spec.bytes,
                    0.,
                );
                tick = Instant::now();
            }
        }
    }
    temp.as_file().sync_all()?;
    verify(temp.path(), &model, cancel, send)?;
    check_cancel(cancel)?;
    temp.persist_noclobber(&path)
        .context("Cannot publish model without replacing existing data")?;
    // Verified download parts and notices are retained, including on errors/cancellation.
    Ok(path)
}

#[cfg(test)]
mod tests;

pub struct AssetJob {
    pub updates: mpsc::Receiver<Update>,
    cancel: Arc<AtomicBool>,
    handle: Option<thread::JoinHandle<()>>,
}
impl AssetJob {
    pub fn download() -> Result<Self> {
        ensure!(
            RELEASE_PUBLISHED,
            "GitHub model release is not published; no download attempted"
        );
        let directory = model_directory()?;
        let spec = catalogue();
        Self::spawn(move |cancel, send| install(&spec, &directory, Path::new("curl"), cancel, send))
    }
    pub fn verify(path: PathBuf) -> Result<Self> {
        Self::spawn(move |cancel, send| {
            let spec = catalogue();
            verify(
                &path,
                &Asset {
                    name: spec.filename,
                    bytes: spec.bytes,
                    sha256: spec.sha256,
                },
                cancel,
                send,
            )?;
            Ok(path)
        })
    }
    fn spawn(
        task: impl FnOnce(&AtomicBool, &mpsc::Sender<Update>) -> Result<PathBuf> + Send + 'static,
    ) -> Result<Self> {
        let cancel = Arc::new(AtomicBool::new(false));
        let stop = cancel.clone();
        let (send, updates) = mpsc::channel();
        let handle = thread::Builder::new()
            .name("model-install".into())
            .spawn(move || {
                let outcome = match task(&stop, &send) {
                    Ok(path) => Update::Ready(path),
                    Err(error) => Update::Failed(format!("{error:#}")),
                };
                let _ = send.send(outcome);
            })?;
        Ok(Self {
            updates,
            cancel,
            handle: Some(handle),
        })
    }
}
impl Drop for AssetJob {
    fn drop(&mut self) {
        self.cancel.store(true, Ordering::Relaxed);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}
