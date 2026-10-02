import Foundation

public struct CLIOptions: Sendable {
    public enum ColorMode: String, Sendable {
        case auto, always, never
    }

    public enum Command: String, Sendable {
        case scan, add, remove, list
    }

    public var command: Command = .scan
    public var paths: [String] = []
    public var fetch = false
    public var watch = false
    public var help = false
    public var color: ColorMode = .auto

    public init(arguments: [String]) throws {
        var index = 0
        if let first = arguments.first, let command = Command(rawValue: first) {
            self.command = command
            index = 1
        }
        var positionalOnly = false
        while index < arguments.count {
            let argument = arguments[index]
            if positionalOnly {
                paths.append(argument)
            } else {
                switch argument {
                case "--": positionalOnly = true
                case "--fetch": fetch = true
                case "--watch": watch = true
                case "--help", "-h": help = true
                case "--color":
                    index += 1
                    guard index < arguments.count,
                          let mode = ColorMode(rawValue: arguments[index]) else {
                        throw PushTrackError("Use auto, always, or never for --color.")
                    }
                    color = mode
                default:
                    guard !argument.hasPrefix("-") else {
                        throw PushTrackError("Unknown option: \(argument). See pushtrack --help.")
                    }
                    paths.append(argument)
                }
            }
            index += 1
        }
        guard !help else { return }
        if (command == .add || command == .remove) && paths.isEmpty {
            throw PushTrackError("\(command.rawValue) requires at least one folder path.")
        }
        if command == .list && !paths.isEmpty {
            throw PushTrackError("The list command does not accept folder paths.")
        }
        if command != .scan && (fetch || watch) {
            throw PushTrackError("--fetch and --watch can only be used when scanning.")
        }
    }

    public func usesColor(isTerminal: Bool, environment: [String: String]) -> Bool {
        switch color {
        case .always: true
        case .never: false
        case .auto: isTerminal && environment["NO_COLOR"] == nil && environment["TERM"] != "dumb"
        }
    }

    public var refreshInterval: TimeInterval { fetch ? 60 : 10 }

    public static let usage = """
    pushtrack — track commit and push status across your projects

    Usage:
      pushtrack [folder ...] [--fetch] [--watch] [--color auto|always|never]
      pushtrack add <folder ...>
      pushtrack remove <folder ...>
      pushtrack list

    Examples:
      pushtrack add ~/Projects ~/Work /Volumes/Disk/Repos
      pushtrack list
      pushtrack remove ~/Work
      pushtrack
      pushtrack ~/Projects
      pushtrack ~/Projects/App1 ~/Work/App2 --fetch
      pushtrack ~/Projects --watch
      pushtrack ~/Projects --fetch --watch

    Options:
      --fetch       Fetch the current branch's configured upstream.
      --watch       Open the interactive dashboard; refresh every 10s (60s with --fetch).
      --color MODE  ANSI colors: auto (default), always, never.
      -h, --help    Show this help.
      --            Treat remaining arguments as folder paths.

    Dashboard: Up/Down to select, Page Up/Down to scroll, Home/End to jump,
    r to refresh, q or Ctrl+C to exit. Requires interactive input and output.

    Without paths, saved folders are scanned; if none are saved, the current
    directory is used. Explicit paths are scanned once without saving them.
    Saved in $XDG_CONFIG_HOME/pushtrack/config.json or
    ~/.config/pushtrack/config.json.
    Discovery searches at most two levels below each folder and stops at repos.
    Worktrees are supported. Only each repository's current branch is checked.

    Without --fetch, counts use cached upstream refs, not the current server state.
    Other branches and alternate push destinations are not checked.
    No commits, pushes, pulls, checkouts, or resets are performed.
    --fetch only updates remote-tracking refs and Git objects.
    NO_COLOR and redirected output disable automatic colors.
    """
}

public struct PushTrackError: Error, LocalizedError, Sendable {
    public let message: String

    public init(_ message: String) { self.message = message }
    public var errorDescription: String? { message }
}
