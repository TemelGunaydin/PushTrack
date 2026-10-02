use clap::{Parser, Subcommand, ValueEnum};
use std::{io::IsTerminal, path::PathBuf};

#[derive(Debug, Parser)]
#[command(
    version,
    about = "Did you push it? Track all your Git projects in one place."
)]
#[command(
    after_help = "Examples:\n  pushtrack add ~/Projects ~/Work\n  pushtrack --fetch --watch\n  pushtrack /path/to/repo\n\nWatch: arrows to select, Page Up/Down to scroll, Tab for details, r to refresh, q to quit.\nOnly the current branch's configured upstream is checked. No commits or pushes are performed."
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<FolderCommand>,
    /// Scan these folders once without changing the saved list
    pub paths: Vec<PathBuf>,
    /// Fetch the current branch's upstream instead of relying on cached refs
    #[arg(long)]
    pub fetch: bool,
    /// Open the full-screen, keyboard-driven dashboard
    #[arg(long)]
    pub watch: bool,
    /// Color output (NO_COLOR disables automatic colors)
    #[arg(long, value_enum, default_value = "auto")]
    pub color: ColorMode,
}

#[derive(Debug, Subcommand)]
pub enum FolderCommand {
    /// Save one or more project folders
    Add {
        #[arg(required = true)]
        paths: Vec<PathBuf>,
    },
    /// Stop tracking folders without deleting any files
    Remove {
        #[arg(required = true)]
        paths: Vec<PathBuf>,
    },
    /// Show saved folders
    List,
}

#[derive(Clone, Copy, Debug, ValueEnum)]
pub enum ColorMode {
    Auto,
    Always,
    Never,
}

impl Cli {
    pub fn colors(&self) -> bool {
        match self.color {
            ColorMode::Always => true,
            ColorMode::Never => false,
            ColorMode::Auto => {
                std::io::stdout().is_terminal()
                    && std::env::var_os("NO_COLOR").is_none()
                    && std::env::var("TERM").as_deref() != Ok("dumb")
            }
        }
    }

    pub fn interval(&self) -> std::time::Duration {
        std::time::Duration::from_secs(if self.fetch { 60 } else { 10 })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn parses_existing_commands_and_flags() {
        let cli = Cli::try_parse_from(["pushtrack", "--fetch", "--watch"]).unwrap();
        assert!(cli.fetch && cli.watch && cli.paths.is_empty());
        let cli = Cli::try_parse_from(["pushtrack", "add", "/a", "/b"]).unwrap();
        assert!(matches!(cli.command, Some(FolderCommand::Add { paths }) if paths.len() == 2));
        let cli = Cli::try_parse_from(["pushtrack", "--", "-repo"]).unwrap();
        assert_eq!(cli.paths, [PathBuf::from("-repo")]);
        assert!(Cli::try_parse_from(["pushtrack", "add"]).is_err());
        assert!(Cli::try_parse_from(["pushtrack", "--color", "purple"]).is_err());
    }
}
