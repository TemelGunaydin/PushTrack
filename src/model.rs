use anyhow::{Result, bail};
use std::{
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

#[derive(Clone, Debug, Default)]
pub struct Snapshot {
    pub branch: String,
    pub oid: String,
    pub upstream: Option<String>,
    pub ahead: Option<usize>,
    pub behind: Option<usize>,
    pub staged: usize,
    pub modified: usize,
    pub untracked: usize,
    pub conflicts: usize,
    pub changed: usize,
}

impl Snapshot {
    pub fn parse(output: &[u8]) -> Result<Self> {
        let mut result = Self::default();
        let mut records = output.split(|b| *b == 0);
        while let Some(record) = records.next() {
            let line = String::from_utf8_lossy(record);
            if let Some(value) = line.strip_prefix("# branch.oid ") {
                result.oid = value.into();
            } else if let Some(value) = line.strip_prefix("# branch.head ") {
                result.branch = value.into();
            } else if let Some(value) = line.strip_prefix("# branch.upstream ") {
                result.upstream = Some(value.into());
            } else if let Some(value) = line.strip_prefix("# branch.ab ") {
                let Some((ahead, behind)) = value.split_once(' ') else {
                    bail!("Invalid Git ahead/behind counts");
                };
                result.ahead = ahead.strip_prefix('+').and_then(|s| s.parse().ok());
                result.behind = behind.strip_prefix('-').and_then(|s| s.parse().ok());
                if result.ahead.is_none() || result.behind.is_none() {
                    bail!("Invalid Git ahead/behind counts");
                }
            } else if line.starts_with("1 ") || line.starts_with("2 ") {
                let xy = record
                    .get(2..4)
                    .ok_or_else(|| anyhow::anyhow!("Invalid Git file status"))?;
                result.staged += usize::from(xy[0] != b'.');
                result.modified += usize::from(xy[1] != b'.');
                result.changed += 1;
                if line.starts_with("2 ") {
                    records.next();
                }
            } else if line.starts_with("? ") {
                result.untracked += 1;
                result.changed += 1;
            } else if line.starts_with("u ") {
                result.conflicts += 1;
                result.changed += 1;
            }
        }
        if result.branch.is_empty() || result.oid.is_empty() {
            bail!("Could not read Git branch information");
        }
        Ok(result)
    }

    pub fn changes(&self) -> String {
        if self.changed == 0 {
            return "clean".into();
        }
        [
            ("S", self.staged),
            ("M", self.modified),
            ("?", self.untracked),
            ("U", self.conflicts),
        ]
        .into_iter()
        .filter(|(_, n)| *n > 0)
        .map(|(label, n)| format!("{label}:{n}"))
        .collect::<Vec<_>>()
        .join("  ")
    }
}

#[derive(Clone, Debug)]
pub enum Verification {
    Cached,
    Fetched(SystemTime),
    Local,
    NoTarget,
    Failed(String),
}

impl Verification {
    pub fn label(&self) -> String {
        match self {
            Self::Cached => "Cached refs · remote not verified".into(),
            Self::Fetched(time) => format!("Fetched at {}", clock(*time)),
            Self::Local => "Local upstream · not a remote check".into(),
            Self::NoTarget => "No upstream to fetch".into(),
            Self::Failed(_) => "Remote not verified".into(),
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum State {
    Synced,
    Ahead,
    Behind,
    Diverged,
    NoUpstream,
    MissingRef,
    Detached,
    Unborn,
    Error,
}

#[derive(Clone, Debug)]
pub struct Report {
    pub path: PathBuf,
    pub snapshot: Option<Snapshot>,
    pub verification: Verification,
    pub error: Option<String>,
}

impl Report {
    pub fn state(&self) -> State {
        if self.error.is_some() || matches!(self.verification, Verification::Failed(_)) {
            return State::Error;
        }
        let Some(snapshot) = &self.snapshot else {
            return State::Error;
        };
        if snapshot.oid == "(initial)" {
            return State::Unborn;
        }
        if snapshot.branch == "(detached)" {
            return State::Detached;
        }
        if snapshot.upstream.is_none() {
            return State::NoUpstream;
        }
        match (snapshot.ahead, snapshot.behind) {
            (Some(a), Some(b)) if a > 0 && b > 0 => State::Diverged,
            (Some(a), Some(_)) if a > 0 => State::Ahead,
            (Some(_), Some(b)) if b > 0 => State::Behind,
            (Some(_), Some(_)) => State::Synced,
            _ => State::MissingRef,
        }
    }

    pub fn status(&self) -> String {
        let ahead = self.snapshot.as_ref().and_then(|s| s.ahead).unwrap_or(0);
        let behind = self.snapshot.as_ref().and_then(|s| s.behind).unwrap_or(0);
        match self.state() {
            State::Synced => "✓ In sync".into(),
            State::Ahead => format!("↑ {ahead} to push"),
            State::Behind => format!("↓ {behind} behind"),
            State::Diverged => format!("↕ {ahead} ahead · {behind} behind"),
            State::NoUpstream => "— No upstream".into(),
            State::MissingRef => "? Upstream ref missing".into(),
            State::Detached => "! Detached HEAD".into(),
            State::Unborn => "— No commits yet".into(),
            State::Error => "! Check failed".into(),
        }
    }

    pub fn needs_push(&self) -> bool {
        matches!(self.state(), State::Ahead | State::Diverged)
    }

    pub fn issue(&self) -> Option<&str> {
        self.error.as_deref().or(match &self.verification {
            Verification::Failed(error) => Some(error),
            _ => None,
        })
    }
}

pub fn clock(time: SystemTime) -> String {
    let seconds = time
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
        % 86400;
    format!(
        "{:02}:{:02}:{:02} UTC",
        seconds / 3600,
        seconds / 60 % 60,
        seconds % 60
    )
}

pub fn safe(text: impl AsRef<str>) -> String {
    text.as_ref()
        .chars()
        .map(|c| {
            if c.is_control() || matches!(c, '\u{202a}'..='\u{202e}' | '\u{2066}'..='\u{2069}') {
                ' '
            } else {
                c
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn classifies_all_history_states() {
        for (a, b, state) in [
            (0, 0, State::Synced),
            (2, 0, State::Ahead),
            (0, 3, State::Behind),
            (2, 3, State::Diverged),
        ] {
            let snapshot = Snapshot::parse(format!("# branch.oid abc\0# branch.head main\0# branch.upstream origin/main\0# branch.ab +{a} -{b}\0").as_bytes()).unwrap();
            let report = Report {
                path: "/repo".into(),
                snapshot: Some(snapshot),
                verification: Verification::Cached,
                error: None,
            };
            assert_eq!(report.state(), state);
        }
    }
    #[test]
    fn malformed_output_is_not_clean() {
        for bytes in [
            b"".as_slice(),
            b"# branch.head main\0",
            b"# branch.oid abc\0# branch.head main\0# branch.ab bad counts\0",
        ] {
            assert!(Snapshot::parse(bytes).is_err());
        }
    }
    #[test]
    fn control_characters_cannot_inject_terminal_commands() {
        assert_eq!(safe("repo\x1b[2J\nname\u{202e}"), "repo [2J name ");
    }
}
