import Foundation

public struct TerminalRenderer {
    public var color: Bool
    public var width: Int

    public init(color: Bool, width: Int = 120) {
        self.color = color
        self.width = max(40, width)
    }

    public func render(reports: [RepositoryReport], warnings: [String], fetch: Bool, watch: Bool, date: Date = Date()) -> String {
        let formatter = Self.clockFormatter()
        let pending = reports.filter(\.needsPush).count
        let dirty = reports.filter { ($0.snapshot?.changedFiles ?? 0) > 0 }.count
        var lines = [
            "",
            "  \(paint(">_ PushTrack", .bold))  \(paint(formatter.string(from: date), .dim))",
            "  \(reports.count) repositories · \(paint("\(pending) to push", pending > 0 ? .yellow : .dim)) · \(dirty) with changes",
            "  \(paint(fetch ? "Remote check: fetch · individual check times below" : "Local view · remote not verified · use --fetch to check", .dim))",
            "",
        ]
        if reports.isEmpty {
            lines.append("  No Git repositories found. Add a repository or its parent folder:")
            lines.append("  pushtrack add /path/to/projects")
        } else if width >= 112 {
            lines.append(paint("  \(fit("PROJECT", 24))  \(fit("BRANCH", 20))  \(fit("STATUS", 26))  WORKTREE", .dim))
            lines.append(paint("  " + String(repeating: "─", count: min(width - 4, 116)), .dim))
        }

        for report in reports {
            let (status, tone) = statusLabel(report)
            let branch = branchLabel(report.snapshot)
            let changes = changesLabel(report.snapshot)
            let changeTone: Tone = (report.snapshot?.conflicts ?? 0) > 0 ? .red : .dim
            if width >= 112 {
                lines.append("  \(paint(fit(report.directory.lastPathComponent, 24), .bold))  \(fit(branch, 20))  \(paint(fit(status, 26), tone))  \(paint(changes, changeTone))")
            } else {
                lines.append("  \(paint(Self.safe(report.directory.lastPathComponent), .bold))  \(paint(Self.safe(branch), .dim))")
                lines.append("    \(paint(status, tone)) · \(paint(changes, changeTone))")
            }
            let upstream = report.snapshot?.upstream.map { " → \($0)" } ?? ""
            lines.append(paint("    \(Self.safe(shortPath(report.directory.path) + upstream)) · \(sourceLabel(report.verification, formatter: formatter))", .dim))
            if let error = report.error {
                lines.append(paint("    \(Self.safe(error))", .red))
            }
            if case .failed(let error) = report.verification {
                lines.append(paint("    Fetch failed; remote not verified: \(Self.safe(error))", .red))
            }
            lines.append("")
        }
        for warning in warnings { lines.append(paint("  ! \(Self.safe(warning))", .yellow)) }
        lines.append(paint("  S: staged · M: modified · ?: untracked · U: conflicts", .dim))
        if watch { lines.append(paint("  Refresh every \(fetch ? 60 : 10)s · exit: Ctrl+C", .dim)) }
        return lines.joined(separator: "\n") + "\n"
    }

    public static func safe(_ text: String) -> String { TerminalText.safe(text) }

    enum Tone: String {
        case green = "32", yellow = "33", red = "31", blue = "34", dim = "2", bold = "1"
        case accent = "38;5;79", border = "38;5;240", muted = "38;5;245"
        case selected = "48;5;236;38;5;159;1", title = "1;38;5;255"
    }

    func paint(_ text: String, _ tone: Tone) -> String {
        color ? "\u{1B}[\(tone.rawValue)m\(text)\u{1B}[0m" : text
    }

    func statusLabel(_ report: RepositoryReport) -> (String, Tone) {
        let ahead = report.snapshot?.ahead ?? 0
        let behind = report.snapshot?.behind ?? 0
        switch report.state {
        case .inSync: return ("✓ In sync", .green)
        case .ahead: return ("↑ \(ahead) to push", .yellow)
        case .behind: return ("↓ \(behind) behind", .blue)
        case .diverged: return ("↕ ↑\(ahead) ↓\(behind) diverged", .red)
        case .noUpstream: return ("— No upstream", .yellow)
        case .missingUpstream: return ("? Upstream ref missing", .yellow)
        case .detached: return ("! Detached HEAD", .yellow)
        case .unborn: return ("— No commits yet", .yellow)
        case .error: return ("! Check failed", .red)
        }
    }

    func branchLabel(_ snapshot: GitSnapshot?) -> String {
        snapshot.map { $0.isDetached ? "detached HEAD" : $0.branch } ?? "—"
    }

    func changesLabel(_ snapshot: GitSnapshot?) -> String {
        guard let snapshot else { return "—" }
        guard snapshot.changedFiles > 0 else { return "clean" }
        var parts: [String] = []
        if snapshot.staged > 0 { parts.append("S:\(snapshot.staged)") }
        if snapshot.unstaged > 0 { parts.append("M:\(snapshot.unstaged)") }
        if snapshot.untracked > 0 { parts.append("?:\(snapshot.untracked)") }
        if snapshot.conflicts > 0 { parts.append("U:\(snapshot.conflicts)") }
        return parts.joined(separator: " ")
    }

    func sourceLabel(_ verification: RemoteVerification, formatter: DateFormatter) -> String {
        switch verification {
        case .cached: "cached refs · remote not verified"
        case .fetched(let date): "fetched at \(formatter.string(from: date))"
        case .localUpstream: "local upstream; not a remote"
        case .notApplicable: "no fetch target"
        case .failed: "remote not verified"
        }
    }

    func shortPath(_ path: String) -> String {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        if path == home { return "~" }
        if path.hasPrefix(home + "/") { return "~" + path.dropFirst(home.count) }
        return path
    }

    func fit(_ text: String, _ length: Int) -> String { TerminalText.fit(text, to: length) }

    static func clockFormatter() -> DateFormatter {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "HH:mm:ss"
        return formatter
    }
}
