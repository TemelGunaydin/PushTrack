//! On-demand staged-only local drafts. Never stages, commits, pushes or downloads.
use crate::{git::Git, process};
use anyhow::{Context, Result, ensure};
use clap::Args;
use std::{
    fs,
    path::{Path, PathBuf},
    process::Command,
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    thread,
    time::Duration,
};

pub const DIFF_CAP: u64 = 4194304;
const CONTEXTS: [usize; 7] = [4096, 8192, 16384, 32768, 65536, 131072, 262144];
const CONNECTOR: &str = include_str!("../ml/local_subject.py");

#[derive(Clone, Debug, Default, Args)]
pub struct LocalOptions {
    /// Pinned Qwen3.5-4B Q4_K_M GGUF (2.74GB); no automatic download
    #[arg(long = "ai-model", requires = "watch")]
    pub ai_model: Option<PathBuf>,
    /// Trusted local llama-server b11429 CPU executable
    #[arg(long = "ai-server", requires = "watch")]
    pub ai_server: Option<PathBuf>,
    /// Python 3.11+ executable for the embedded standard-library connector
    #[arg(long = "ai-python", requires = "watch")]
    pub ai_python: Option<PathBuf>,
}

impl LocalOptions {
    pub fn config(&self) -> Result<LocalConfig> {
        let cwd = std::env::current_dir()?;
        let python = self.ai_python.clone().unwrap_or_else(|| "python3".into());
        let python = if python.components().count() > 1 || python.is_absolute() {
            cwd.join(python)
        } else {
            python
        };
        let model = match &self.ai_model {
            Some(path) => cwd.join(path),
            None => crate::assets::model_path()?,
        };
        ensure!(
            model.is_file(),
            "Select/download the local model with a, or set --ai-model"
        );
        let server = resolve_server(
            self.ai_server.as_deref(),
            &cwd,
            std::env::var_os("PATH").as_deref(),
            crate::assets::cached_runtime_path().ok().flatten(),
        )?;
        Ok(LocalConfig {
            model,
            server,
            python,
        })
    }
}
fn resolve_server(
    explicit: Option<&Path>,
    cwd: &Path,
    search: Option<&std::ffi::OsStr>,
    cached: Option<PathBuf>,
) -> Result<PathBuf> {
    if let Some(path) = explicit {
        return Ok(cwd.join(path));
    }
    search.and_then(|paths|std::env::split_paths(paths).map(|path|path.join("llama-server")).find(|path|path.is_file()))
        .or_else(||cached.filter(|path|path.is_file()))
        .context("Trusted llama-server b11429 not found on PATH/in supported cache; set --ai-server. No runtime download attempted")
}

#[cfg(test)]
mod config_tests {
    use super::*;
    #[test]
    fn runtime_lookup_preserves_explicit_path_and_path_priority() {
        let root = tempfile::tempdir().unwrap();
        let path = root.path().join("path");
        fs::create_dir(&path).unwrap();
        let on_path = path.join("llama-server");
        fs::write(&on_path, b"synthetic executable").unwrap();
        let cached = root.path().join("cached-server");
        fs::write(&cached, b"cached fixture").unwrap();
        let search = std::env::join_paths([&path]).unwrap();
        assert_eq!(
            resolve_server(
                Some(Path::new("explicit-server")),
                root.path(),
                Some(&search),
                Some(cached.clone())
            )
            .unwrap(),
            root.path().join("explicit-server")
        );
        assert_eq!(
            resolve_server(None, root.path(), Some(&search), Some(cached)).unwrap(),
            on_path
        );
    }
    #[test]
    fn installed_cache_is_found_without_path_and_missing_cache_refuses() {
        let root = tempfile::tempdir().unwrap();
        let cached = root.path().join("llama-server");
        fs::write(&cached, b"synthetic installed runtime").unwrap();
        assert_eq!(
            resolve_server(None, root.path(), None, Some(cached.clone())).unwrap(),
            cached
        );
        fs::remove_file(cached).unwrap();
        assert!(
            resolve_server(None, root.path(), None, Some(root.path().join("missing")))
                .unwrap_err()
                .to_string()
                .contains("No runtime download attempted")
        );
    }
}

#[derive(Clone, Debug)]
pub struct LocalConfig {
    pub model: PathBuf,
    pub server: PathBuf,
    pub python: PathBuf,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct StagedDiff {
    pub path: PathBuf,
    pub diff: String,
    pub files: usize,
    head: Vec<u8>,
    branch: Vec<u8>,
    raw: Vec<u8>,
}

fn checked(git: &Git, path: &Path, args: &[&str]) -> Result<Vec<u8>> {
    let output = git.run_bounded(path, args, Some(DIFF_CAP)).context("Complete staged input limit is 4MiB; no files/hunks may be omitted. Reduce the staged scope manually if this limit is exceeded")?;
    ensure!(
        output.status.success(),
        "Git staged-diff collection failed: {}",
        output.stderr.trim()
    );
    Ok(output.stdout)
}
fn optional_ref(git: &Git, path: &Path, args: &[&str]) -> Result<Vec<u8>> {
    let output = git.run_bounded(path, args, Some(DIFF_CAP))?;
    ensure!(
        output.status.success() || output.status.code() == Some(1),
        "Cannot read repository identity: {}",
        output.stderr.trim()
    );
    Ok(output.stdout)
}
fn raw_files(raw: &[u8]) -> Result<usize> {
    let mut chunks = raw.split(|byte| *byte == 0);
    let mut count = 0;
    while let Some(metadata) = chunks.next() {
        if metadata.is_empty() {
            continue;
        }
        let fields: Vec<_> = std::str::from_utf8(metadata)?.split_whitespace().collect();
        ensure!(
            fields.len() == 5 && fields[0].starts_with(':'),
            "Unsupported staged diff metadata"
        );
        ensure!(
            matches!(fields[4], "A" | "M" | "D" | "T"),
            "Conflicts or unsupported staged changes; resolve before generating a draft"
        );
        for mode in [fields[0].trim_start_matches(':'), fields[1]] {
            ensure!(
                matches!(mode, "000000" | "100644" | "100755"),
                "Symlinks/submodules are unsupported; no staged files were omitted"
            );
        }
        let name = std::str::from_utf8(chunks.next().context("Incomplete staged filename")?)?;
        ensure!(
            !name.is_empty() && !name.chars().any(forbidden),
            "Unsupported staged filename controls/encoding"
        );
        count += 1;
    }
    ensure!(
        count > 0,
        "No staged changes. Stage the intended text changes yourself, then press m. Unstaged/untracked files are not included."
    );
    Ok(count)
}
impl StagedDiff {
    pub fn capture(git: &Git, path: &Path) -> Result<Self> {
        let first = Self::once(git, path)?;
        let second = Self::once(git, path)?;
        ensure!(
            first == second,
            "Repository changed during collection; regenerate the draft"
        );
        Ok(first)
    }
    fn once(git: &Git, path: &Path) -> Result<Self> {
        let root = checked(git, path, &["rev-parse", "--show-toplevel"])?;
        let root = std::str::from_utf8(&root)?
            .strip_suffix('\n')
            .context("Unsupported repository path")?;
        ensure!(
            fs::canonicalize(root)? == fs::canonicalize(path)?,
            "Select the repository root for a draft"
        );
        let head = optional_ref(git, path, &["rev-parse", "--verify", "--quiet", "HEAD"])?;
        let branch = optional_ref(git, path, &["symbolic-ref", "--quiet", "HEAD"])?;
        let common = [
            "diff",
            "--cached",
            "--no-ext-diff",
            "--no-textconv",
            "--no-color",
            "--no-renames",
            "--ignore-submodules=none",
            "--no-relative",
        ];
        let mut args = common.to_vec();
        args.extend(["--raw", "-z", "--no-abbrev"]);
        let raw = checked(git, path, &args)?;
        let files = raw_files(&raw)?;
        args = common.to_vec();
        args.extend(["--numstat", "-z"]);
        let stat = checked(git, path, &args)?;
        let stats: Vec<_> = stat
            .split(|byte| *byte == 0)
            .filter(|row| !row.is_empty())
            .collect();
        ensure!(
            stats.len() == files,
            "Incomplete staged file accounting; no files may be omitted"
        );
        for row in stats {
            let fields: Vec<_> = row.splitn(3, |byte| *byte == b'\t').collect();
            ensure!(
                fields.len() == 3 && fields[0] != b"-" && fields[1] != b"-",
                "Binary staged files are unsupported; no files were omitted"
            );
        }
        args = common.to_vec();
        args.extend([
            "--patch",
            "--full-index",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            "--unified=3",
            "--inter-hunk-context=0",
            "--diff-algorithm=myers",
            "--no-indent-heuristic",
        ]);
        let diff = String::from_utf8(checked(git, path, &args)?)
            .context("Staged diff is not UTF-8; no conversion allowed")?;
        ensure!(
            diff.starts_with("diff --git ")
                && diff
                    .lines()
                    .filter(|line| line.starts_with("diff --git "))
                    .count()
                    == files,
            "Incomplete staged patch; no files may be omitted"
        );
        ensure!(
            !diff.contains("\nGIT binary patch\n")
                && !diff.lines().any(|line| line.starts_with("Binary files ")),
            "Binary staged files are unsupported"
        );
        ensure!(
            !diff
                .chars()
                .any(|c| forbidden(c) && !matches!(c, '\t' | '\n' | '\r')),
            "Unsupported diff controls; no sanitization allowed"
        );
        ensure!(
            head == optional_ref(git, path, &["rev-parse", "--verify", "--quiet", "HEAD"])?
                && branch == optional_ref(git, path, &["symbolic-ref", "--quiet", "HEAD"])?,
            "HEAD or branch changed during collection"
        );
        Ok(Self {
            path: fs::canonicalize(path)?,
            diff,
            files,
            head,
            branch,
            raw,
        })
    }
    pub fn verify(&self, git: &Git) -> Result<()> {
        ensure!(
            *self == Self::capture(git, &self.path)?,
            "Staged changes or HEAD changed; discard this draft and regenerate"
        );
        Ok(())
    }
}

pub fn forbidden(c: char) -> bool {
    c.is_control()
        || matches!(c,'\u{200b}'..='\u{200f}'|'\u{202a}'..='\u{202e}'|'\u{2060}'..='\u{206f}'|'\u{feff}')
}
pub fn validate_subject(value: &str) -> Result<()> {
    ensure!(
        !value.is_empty()
            && value == value.trim()
            && value.chars().count() <= 72
            && !value.chars().any(forbidden),
        "Expected a nonempty single-line subject of at most72characters without controls"
    );
    ensure!(
        !value.starts_with(['\"', '\'', '`', '#'])
            && !value.starts_with("- ")
            && !value.starts_with("* ")
            && !value.contains("<|"),
        "Unexpected subject formatting/control markers"
    );
    Ok(())
}
#[derive(Clone, Debug, serde::Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Capacity {
    pub diff_bytes: usize,
    pub diff_tokens: usize,
    pub prompt_tokens: usize,
    pub output_tokens: usize,
    pub context: usize,
    pub suggested_context: Option<usize>,
}
impl Capacity {
    fn validate(&self, input: &StagedDiff, context: usize) -> Result<()> {
        let required = self
            .prompt_tokens
            .checked_add(self.output_tokens)
            .context("Invalid capacity token count")?;
        ensure!(
            self.diff_bytes == input.diff.len()
                && self.diff_tokens > 0
                && self.prompt_tokens > 0
                && self.output_tokens == 192
                && self.context == context
                && CONTEXTS.contains(&context)
                && required > context
                && self.suggested_context
                    == CONTEXTS.iter().copied().find(|size| *size >= required),
            "Invalid complete-input capacity report"
        );
        Ok(())
    }
}
fn generate(
    git: &Git,
    input: &StagedDiff,
    config: &LocalConfig,
    context: usize,
) -> Result<DraftResult> {
    let temp = tempfile::tempdir()?;
    let script = temp.path().join("local_subject.py");
    fs::write(&script, CONNECTOR)?;
    let model =
        fs::canonicalize(&config.model).context("Local GGUF not found; no download attempted")?;
    let server = fs::canonicalize(&config.server)
        .context("Local CPU server not found; no download attempted")?;
    let mut version = Command::new(&server);
    version.arg("--version");
    let version = process::run(
        version,
        None,
        &git.cancel,
        Duration::from_secs(10),
        Some(4096),
        "Local CPU runtime check",
    )?;
    let version_text = format!(
        "{}{}",
        String::from_utf8_lossy(&version.stdout),
        version.stderr
    );
    ensure!(
        version.status.success()
            && version_text.contains("commit d81235049")
            && !version_text.contains("dirty"),
        "Expected trusted llama.cpp b11429 (commit d81235049); no download attempted"
    );
    let mut command = Command::new(&config.python);
    command
        .args(["-I", "-S", "-X", "utf8"])
        .arg(script)
        .arg("--model")
        .arg(model)
        .arg("--server")
        .arg(server)
        .arg("--capacity-report")
        .arg("--context")
        .arg(context.to_string())
        .current_dir(temp.path())
        // Keep Python/server temporary logs inside the Rust-owned directory, including on cancellation.
        .env("TMPDIR", temp.path());
    let output = process::run(
        command,
        Some(input.diff.as_bytes()),
        &git.cancel,
        Duration::from_secs(300),
        Some(4096),
        "Local draft generation",
    )?;
    if output.status.code() == Some(2) {
        let capacity: Capacity =
            serde_json::from_slice(&output.stdout).context("Invalid capacity JSON")?;
        capacity.validate(input, context)?;
        input.verify(git)?;
        return Ok(DraftResult::Capacity(input.clone(), capacity));
    }
    ensure!(
        output.status.success(),
        "Local draft generation failed: {}",
        output.stderr.trim()
    );
    let stdout = String::from_utf8(output.stdout).context("Local subject is not UTF-8")?;
    let value = stdout
        .strip_suffix('\n')
        .context("Incomplete local subject output")?;
    let value = value.strip_suffix('\r').unwrap_or(value);
    validate_subject(value)?;
    input.verify(git)?;
    Ok(DraftResult::Generated(input.clone(), value.into()))
}

pub enum DraftResult {
    Collected(StagedDiff),
    Capacity(StagedDiff, Capacity),
    Generated(StagedDiff, String),
    Reviewed,
    Failed(String),
}
pub struct DraftJob {
    pub updates: mpsc::Receiver<DraftResult>,
    cancel: Arc<AtomicBool>,
    handle: Option<thread::JoinHandle<()>>,
}
impl DraftJob {
    pub fn start(path: PathBuf, config: Result<LocalConfig>) -> Result<Self> {
        Self::spawn(move |git, send| {
            let config = config?;
            let input = StagedDiff::capture(git, &path)?;
            let _ = send.send(DraftResult::Collected(input.clone()));
            generate(git, &input, &config, 4096)
        })
    }
    pub fn expand(
        input: StagedDiff,
        capacity: Capacity,
        config: Result<LocalConfig>,
    ) -> Result<Self> {
        capacity.validate(&input, capacity.context)?;
        let context=capacity.suggested_context.context("Complete prompt exceeds maximum 262144 context; reduce staged scope manually, no files/hunks omitted")?;
        Self::spawn(move |git, _| {
            let config = config?;
            input.verify(git)?;
            generate(git, &input, &config, context)
        })
    }
    pub fn review(input: StagedDiff, text: String) -> Result<Self> {
        Self::spawn(move |git, _| {
            validate_subject(&text)?;
            input.verify(git)?;
            Ok(DraftResult::Reviewed)
        })
    }
    fn spawn(
        task: impl FnOnce(&Git, &mpsc::Sender<DraftResult>) -> Result<DraftResult> + Send + 'static,
    ) -> Result<Self> {
        let cancel = Arc::new(AtomicBool::new(false));
        let stop = cancel.clone();
        let (send, updates) = mpsc::channel();
        let handle = thread::Builder::new()
            .name("local-draft".into())
            .spawn(move || {
                let git = Git {
                    cancel: stop,
                    ..Git::default()
                };
                let result = task(&git, &send)
                    .unwrap_or_else(|error| DraftResult::Failed(format!("{error:#}")));
                let _ = send.send(result);
            })?;
        Ok(Self {
            updates,
            cancel,
            handle: Some(handle),
        })
    }
}
impl Drop for DraftJob {
    fn drop(&mut self) {
        self.cancel.store(true, Ordering::Relaxed);
        if let Some(handle) = self.handle.take() {
            let _ = handle.join();
        }
    }
}
