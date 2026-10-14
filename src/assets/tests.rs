use super::*;
use std::os::unix::fs::{PermissionsExt, symlink};

struct Fixture {
    root: tempfile::TempDir,
    spec: ModelSpec,
    curl: PathBuf,
    payload: PathBuf,
    cache: PathBuf,
}
fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
impl Fixture {
    fn new() -> Result<Self> {
        let root = tempfile::tempdir()?;
        let payload = root.path().join("payload");
        fs::create_dir(&payload)?;
        let cache = root.path().join("cache");
        let one = b"GGUF-fixture-";
        let two = b"no-model-inference";
        let bytes = [one.as_slice(), two.as_slice()].concat();
        let asset = |name: &str, data: &[u8]| Asset {
            name: name.into(),
            bytes: data.len() as u64,
            sha256: digest(data),
        };
        let parts = vec![asset("part01", one), asset("part02", two)];
        let notices = vec![asset("LICENSE.txt", b"synthetic license fixture")];
        fs::write(payload.join("part01"), one)?;
        fs::write(payload.join("part02"), two)?;
        fs::write(payload.join("LICENSE.txt"), b"synthetic license fixture")?;
        let spec = ModelSpec {
            id: "fixture".into(),
            name: "Synthetic".into(),
            filename: "fixture.gguf".into(),
            bytes: bytes.len() as u64,
            sha256: digest(&bytes),
            license: "test".into(),
            publisher: "test".into(),
            release_tag: "fixture-v1".into(),
            repository: "TemelGunaydin/PushTrack".into(),
            parts,
            notices,
        };
        let curl = root.path().join("fake-curl");
        let fixture = Self {
            root,
            spec,
            curl,
            payload,
            cache,
        };
        fixture.script("")?;
        Ok(fixture)
    }
    fn script(&self, extra: &str) -> Result<()> {
        fs::write(
            &self.curl,
            format!(
                r#"#!/bin/sh
out=''; headers=''; offset=0; url=''
while [ $# -gt 0 ]; do
 case "$1" in
  --output) out="$2"; shift 2;;
  --dump-header) headers="$2"; shift 2;;
  --continue-at) offset="$2"; shift 2;;
  --url) url="$2"; shift 2;;
  *) shift;;
 esac
done
printf '%s\n' "$url" >> '{root}/requests'
src='{payload}'/"${{url##*/}}"
size=$(wc -c < "$src")
size=$((size))
{extra}
if [ "$offset" -gt 0 ]; then
 printf 'HTTP/1.1 206 Partial Content\r\nContent-Range: bytes %s-%s/%s\r\n\r\n' "$offset" "$((size-1))" "$size" > "$headers"
else
 printf 'HTTP/1.1 200 OK\r\nContent-Length: %s\r\n\r\n' "$size" > "$headers"
fi
dd if="$src" bs=1 skip="$offset" 2>/dev/null >> "$out"
"#,
                root = self.root.path().display(),
                payload = self.payload.display()
            ),
        )?;
        fs::set_permissions(&self.curl, fs::Permissions::from_mode(0o700))?;
        Ok(())
    }
    fn install(&self) -> Result<PathBuf> {
        let (send, _) = mpsc::channel();
        install(
            &self.spec,
            &self.cache,
            &self.curl,
            &AtomicBool::new(false),
            &send,
        )
    }
}
#[test]
fn catalogue_matches_pinned_model_and_all_parts_notices_are_bound() -> Result<()> {
    let spec = catalogue();
    validate(&spec)?;
    assert_eq!(spec.bytes, 2740937888);
    assert_eq!(
        spec.sha256,
        "00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4"
    );
    assert_eq!(spec.parts.len(), 6);
    assert!(spec.parts.iter().all(|part| part.bytes <= 536870912));
    assert_eq!(spec.notices.len(), 4);
    Ok(())
}
#[test]
fn installed_model_is_exact_atomic_and_has_license_files_without_redownload() -> Result<()> {
    let f = Fixture::new()?;
    let path = f.install()?;
    let bytes = [
        fs::read(f.payload.join("part01"))?,
        fs::read(f.payload.join("part02"))?,
    ]
    .concat();
    assert_eq!(fs::read(&path)?, bytes);
    assert!(f.cache.join("LICENSE.txt").exists());
    assert!(!f.cache.join(".download.lock").exists());
    let before = fs::read(f.root.path().join("requests"))?;
    assert_eq!(f.install()?, path);
    assert_eq!(fs::read(f.root.path().join("requests"))?, before);
    Ok(())
}
#[test]
fn partial_resume_preserves_prefix_and_requires_exact_range() -> Result<()> {
    let f = Fixture::new()?;
    fs::create_dir(&f.cache)?;
    let prefix = &fs::read(f.payload.join("part01"))?[..4];
    fs::write(f.cache.join("part01.partial"), prefix)?;
    f.install()?;
    assert_eq!(&fs::read(f.cache.join("part01"))?[..4], prefix);
    let f = Fixture::new()?;
    fs::create_dir(&f.cache)?;
    fs::write(f.cache.join("part01.partial"), b"GGUF")?;
    f.script("printf 'HTTP/1.1 200 OK\\r\\n\\r\\n' > \"$headers\"\ndd if=\"$src\" bs=1 skip=\"$offset\" 2>/dev/null >> \"$out\"\nexit 0")?;
    assert!(f.install().unwrap_err().to_string().contains("HTTP206"));
    assert!(f.cache.join("part01.partial").exists());
    assert!(!f.cache.join("fixture.gguf").exists());
    Ok(())
}
#[test]
fn corrupt_partial_or_model_is_preserved_never_overwritten() -> Result<()> {
    let f = Fixture::new()?;
    fs::create_dir(&f.cache)?;
    let wrong = vec![b'x'; f.spec.parts[0].bytes as usize];
    fs::write(f.cache.join("part01.partial"), &wrong)?;
    assert!(f.install().unwrap_err().to_string().contains("SHA-256"));
    assert_eq!(fs::read(f.cache.join("part01.partial"))?, wrong);
    assert!(!f.cache.join("fixture.gguf").exists());
    let f = Fixture::new()?;
    fs::create_dir(&f.cache)?;
    fs::write(f.cache.join("fixture.gguf"), b"wrong existing")?;
    assert!(f.install().is_err());
    assert_eq!(fs::read(f.cache.join("fixture.gguf"))?, b"wrong existing");
    Ok(())
}
#[test]
fn symlink_oversized_partial_and_locks_are_fail_closed() -> Result<()> {
    let f = Fixture::new()?;
    fs::create_dir(&f.cache)?;
    let other = f.root.path().join("protected");
    fs::write(&other, b"private fixture")?;
    symlink(&other, f.cache.join("part01.partial"))?;
    assert!(f.install().is_err());
    assert_eq!(fs::read(&other)?, b"private fixture");
    fs::remove_file(f.cache.join("part01.partial"))?;
    fs::write(f.cache.join("part01.partial"), vec![b'x'; 100])?;
    assert!(f.install().is_err());
    assert_eq!(fs::metadata(f.cache.join("part01.partial"))?.len(), 100);
    fs::write(f.cache.join(".download.lock"), b"earlier job")?;
    assert!(f.install().unwrap_err().to_string().contains("locked"));
    assert_eq!(fs::read(f.cache.join(".download.lock"))?, b"earlier job");
    Ok(())
}
#[test]
fn network_failure_has_no_retry_and_keeps_partial_and_no_final_model() -> Result<()> {
    let f = Fixture::new()?;
    f.script("printf 'GG' >> \"$out\"\nprintf 'HTTP403 fixture' >&2\nexit 22")?;
    assert!(
        f.install()
            .unwrap_err()
            .to_string()
            .contains("no automatic retry")
    );
    assert_eq!(fs::read(f.cache.join("part01.partial"))?, b"GG");
    assert_eq!(
        fs::read_to_string(f.root.path().join("requests"))?
            .lines()
            .count(),
        1
    );
    assert!(!f.cache.join("fixture.gguf").exists());
    Ok(())
}
#[test]
fn cancellation_drops_owned_download_descendant_and_keeps_partial() -> Result<()> {
    let f = Fixture::new()?;
    let pid = f.root.path().join("child.pid");
    f.script(&format!(
        "printf 'GG' >> \"$out\"\nsleep 60 &\necho $! > '{}'\nwait\nexit 0",
        pid.display()
    ))?;
    let spec = f.spec.clone();
    let cache = f.cache.clone();
    let curl = f.curl.clone();
    let job = AssetJob::spawn(move |cancel, send| install(&spec, &cache, &curl, cancel, send))?;
    let deadline = Instant::now() + Duration::from_secs(4);
    while !pid.exists() && Instant::now() < deadline {
        thread::sleep(Duration::from_millis(10));
    }
    assert!(pid.exists());
    let child: i32 = fs::read_to_string(&pid)?.trim().parse()?;
    drop(job);
    let deadline = Instant::now() + Duration::from_secs(2);
    while nix::sys::signal::kill(nix::unistd::Pid::from_raw(child), None).is_ok()
        && Instant::now() < deadline
    {
        thread::sleep(Duration::from_millis(20));
    }
    assert!(nix::sys::signal::kill(nix::unistd::Pid::from_raw(child), None).is_err());
    assert_eq!(fs::read(f.cache.join("part01.partial"))?, b"GG");
    assert!(!f.cache.join(".download.lock").exists());
    Ok(())
}
#[test]
fn incomplete_or_duplicate_catalogue_cannot_select_arbitrary_files() -> Result<()> {
    let f = Fixture::new()?;
    let mut spec = f.spec.clone();
    spec.parts[0].name = "../overwrite".into();
    assert!(validate(&spec).is_err());
    let mut spec = f.spec.clone();
    spec.parts[1].bytes += 1;
    assert!(validate(&spec).is_err());
    let mut spec = f.spec.clone();
    spec.notices.push(spec.parts[0].clone());
    assert!(validate(&spec).is_err());
    let mut spec = f.spec.clone();
    spec.repository = "unknown/mirror".into();
    assert!(validate(&spec).is_err());
    Ok(())
}
