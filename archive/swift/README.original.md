<p align="center">
  <img src="assets/pushtrack-icon.png" width="144" alt="PushTrack icon">
</p>

<h1 align="center">PushTrack</h1>

<p align="center">Did you push it? Check all your projects from one colorful terminal dashboard.</p>

PushTrack is a dependency-free Swift command-line tool for tracking Git repositories across multiple folders. Whether you work with Pi, another coding agent, or your editor, it helps you spot commits waiting to be pushed and changes waiting to be committed.

**It never commits, pushes, pulls, checks out, or resets anything.** Network access is opt-in with `--fetch`.

## Features

- Track any number of project folders, including external drives.
- Save, list, and remove folders; no hardcoded `~/Projects` default.
- See ahead, behind, diverged, and equal states for the current branch.
- Count staged, modified, untracked, and conflicted files separately.
- Clearly identify missing upstreams, detached HEADs, and repositories without commits.
- Distinguish cached local information from a successful remote fetch.
- Refresh automatically with watch mode.
- Use ANSI colors, compact output for narrow terminals, or plain text for pipes.
- Discover linked Git worktrees as well as ordinary repositories.

Terminal messages are currently in Turkish. Commands and flags are in English.

## Requirements

- Swift 6.2 or newer.
- Git 2.40 or newer, available on `PATH`.
- macOS 13 or newer is the currently supported platform. This is a terminal application, not a GUI app.

On macOS, use an Xcode installation with a compatible Swift compiler and SDK. The commands below use `xcrun swift` to avoid mixing a separately installed Swift toolchain with a newer Xcode SDK.

## Install

```bash
git clone https://github.com/TemelGunaydin/PushTrack.git
cd PushTrack
./scripts/install.sh
```

The installer builds a release binary and copies it to `~/.local/bin/pushtrack`. It does not require `sudo` or modify your shell configuration.

If needed, add this line to your shell configuration, such as `~/.zshrc`, and open a new terminal:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To choose another installation location:

```bash
PREFIX="$HOME/tools" ./scripts/install.sh
```

Or run directly from the source tree without installing:

```bash
xcrun swift run pushtrack --help
xcrun swift run pushtrack /path/to/projects
```

## Quick start

Register the folders you want to monitor. Each may be an individual repository or a directory containing projects:

```bash
pushtrack add ~/Projects ~/Work /Volumes/External/Repos
pushtrack list
```

Then check every saved folder from anywhere:

```bash
pushtrack
pushtrack --fetch
pushtrack --watch
pushtrack --fetch --watch
```

Remove a folder without deleting any files:

```bash
pushtrack remove ~/Work
```

To inspect other folders just once, pass their paths directly. This does not change your saved list:

```bash
pushtrack ~/SideProjects /path/to/another/repo --fetch
pushtrack "/path/with spaces/project"
```

Without explicit paths, PushTrack scans the saved folders. If none are saved, it scans the current directory. A named folder that is missing or unavailable is reported rather than silently ignored.

## Reading the dashboard

| Color / symbol | Meaning |
| --- | --- |
| Green `✓` | Current branch and its upstream reference are equal. |
| Yellow `↑` | Local commits are ahead of the upstream reference. |
| Blue `↓` | The branch is behind its upstream reference. |
| Red `↕` | Both sides have commits the other does not: the histories have diverged. |
| Yellow `—` / `!` / `?` | No upstream, no commits, detached HEAD, or missing upstream reference. |
| Red `!` | A Git operation or remote check failed. Do not assume the repository is synchronized. |

Working-tree counts are independent of branch synchronization:

- `S`: staged files.
- `M`: modified but unstaged files.
- `?`: untracked files, excluding ignored files.
- `U`: merge conflicts.

A file changed both in the index and working tree can contribute to both `S` and `M`. A branch can be equal to its upstream while still having uncommitted changes.

### Local information is not remote verification

By default, PushTrack reads local Git metadata only. A cached `origin/main` reference can be stale, so **a green local result does not prove that the server is currently synchronized**.

Use `--fetch` to refresh the current branch's configured upstream. Each successful check shows its fetch time. Authentication failures, timeouts, unavailable remotes, and deleted remote branches are displayed as failures, never as verified green results. An upstream pointing to another local branch is explicitly labeled as local, not a remote check.

A fetch reflects a point in time; another user can change the remote afterward.

### Scope and safety

- Only the **currently checked-out branch** is compared with its **configured upstream**. Other branches, tags, stashes, and alternate push destinations are not checked. If `pushRemote`, `remote.pushDefault`, a separate push URL, or a custom push refspec sends commits somewhere else, this dashboard does not verify that destination.
- `--fetch` downloads Git objects and updates the relevant remote-tracking reference. It does not change local branches, the index, or working-tree files. Tags, submodule fetching, and automatic maintenance are disabled. Custom fetch refmaps are not allowed to update additional refs.
- Without `--fetch`, PushTrack does not contact remotes. Optional index writes and filesystem-monitor hooks are disabled during status checks.
- Existing Git credentials and SSH configuration are used. Interactive credential prompts are disabled. Each Git subprocess has a 20-second timeout; private repositories require working non-interactive authentication.
- No commands are run through a shell by PushTrack itself. As with ordinary Git, repository configuration may invoke Git credential or transport helpers; only inspect repositories you trust.

## Discovery and saved folders

PushTrack checks each selected folder and searches up to **two directory levels below it**. Once it finds a repository, it does not descend into that repository. For deeper projects or nested repositories, add the repository or its closer parent explicitly.

Hidden directories and common dependency/build directories are skipped during discovery. Symlinked subdirectories are not followed; explicitly supplied symlink paths are resolved. Overlapping roots do not produce duplicate repository rows. Bare repositories are not shown.

Folders are stored as absolute paths in:

```text
$XDG_CONFIG_HOME/pushtrack/config.json
```

If `XDG_CONFIG_HOME` is unset or not an absolute path, the default is:

```text
~/.config/pushtrack/config.json
```

Configuration is written atomically. An unreadable or malformed configuration produces an error instead of being overwritten.

## Watch mode and colors

```bash
pushtrack --watch                 # Local refresh every 10 seconds
pushtrack --fetch --watch         # Fetch and refresh every 60 seconds
pushtrack --color always          # Force ANSI colors
pushtrack --color never           # Plain text
NO_COLOR=1 pushtrack              # Disable automatic colors
pushtrack > status.txt            # Automatically use plain text
```

Intervals begin after each scan finishes. Watch mode requires an interactive terminal; use **Ctrl+C** to exit. Saved folders are reloaded each cycle, so you can add or remove folders from another terminal.

Color defaults to `auto`. Redirected output, `NO_COLOR`, and `TERM=dumb` disable automatic colors. An explicit `--color always` overrides automatic detection. Watch mode still uses terminal-control sequences to refresh its screen, even when colors are disabled.

Use `--` before paths beginning with a dash, or `./` for a directory whose name is also a command:

```bash
pushtrack -- ./-project
pushtrack ./add
```

## Development

```bash
xcrun swift build
xcrun swift test
xcrun swift build -c release
```

The project has no third-party Swift package dependencies. Tests use Swift Testing and temporary local Git repositories, including bare remotes and worktrees. They do not access GitHub or modify your real projects.

Tests cover status parsing, ahead/behind/diverged histories, successful pushes, stale references, deleted branches, fetch failures, preservation of local branches and working files, rename paths, conflicts, persistent folders, color behavior, and subprocess cleanup.

### Exit codes

- `0`: the command completed. Pending commits and uncommitted changes are not execution errors.
- `1`: invalid arguments, configuration or discovery errors, no repositories found, or a Git/fetch failure.
- `130`: interrupted with Ctrl+C while scanning or watching.
- `143`: terminated with SIGTERM while scanning or watching.

Watch mode keeps running after per-repository failures so the next refresh can retry.
