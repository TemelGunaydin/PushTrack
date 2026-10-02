import Foundation

public struct GitSnapshot: Sendable {
    public var branch: String = ""
    public var oid: String = ""
    public var upstream: String?
    public var ahead: Int?
    public var behind: Int?
    public var staged = 0
    public var unstaged = 0
    public var untracked = 0
    public var conflicts = 0
    public var changedFiles = 0

    public var isDetached: Bool { branch == "(detached)" }
    public var isUnborn: Bool { oid == "(initial)" }

    public static func parse(_ output: String) throws -> GitSnapshot {
        var snapshot = GitSnapshot()
        let records = output.split(separator: "\0", omittingEmptySubsequences: false)
        var index = 0
        while index < records.count {
            let record = String(records[index])
            switch record {
            case let line where line.hasPrefix("# branch.oid "):
                snapshot.oid = String(line.dropFirst("# branch.oid ".count))
            case let line where line.hasPrefix("# branch.head "):
                snapshot.branch = String(line.dropFirst("# branch.head ".count))
            case let line where line.hasPrefix("# branch.upstream "):
                snapshot.upstream = String(line.dropFirst("# branch.upstream ".count))
            case let line where line.hasPrefix("# branch.ab "):
                let counts = line.dropFirst("# branch.ab ".count).split(separator: " ")
                guard counts.count == 2, counts[0].first == "+", counts[1].first == "-",
                      let ahead = Int(counts[0].dropFirst()), ahead >= 0,
                      let behind = Int(counts[1].dropFirst()), behind >= 0 else {
                    throw PushTrackError("Could not parse Git ahead/behind counts.")
                }
                snapshot.ahead = ahead
                snapshot.behind = behind
            case let line where line.hasPrefix("1 ") || line.hasPrefix("2 "):
                let fields = line.split(separator: " ", maxSplits: 2)
                guard fields.count == 3, fields[1].count == 2 else {
                    throw PushTrackError("Could not parse Git file status.")
                }
                if fields[1].first != "." { snapshot.staged += 1 }
                if fields[1].last != "." { snapshot.unstaged += 1 }
                snapshot.changedFiles += 1
                // A rename has a second NUL-delimited record containing its old path.
                if line.hasPrefix("2 ") { index += 1 }
            case let line where line.hasPrefix("? "):
                snapshot.untracked += 1
                snapshot.changedFiles += 1
            case let line where line.hasPrefix("u "):
                snapshot.conflicts += 1
                snapshot.changedFiles += 1
            default:
                break
            }
            index += 1
        }
        guard !snapshot.branch.isEmpty, !snapshot.oid.isEmpty else {
            throw PushTrackError("Could not read Git branch information.")
        }
        return snapshot
    }
}

public enum RemoteVerification: Sendable {
    case cached
    case fetched(Date)
    case localUpstream
    case notApplicable
    case failed(String)
}

public enum RepositoryState: Sendable {
    case inSync, ahead, behind, diverged, noUpstream, missingUpstream, detached, unborn, error
}

public struct RepositoryReport: Sendable {
    public let directory: URL
    public var snapshot: GitSnapshot?
    public var verification: RemoteVerification
    public var error: String?

    public init(directory: URL, snapshot: GitSnapshot? = nil, verification: RemoteVerification = .cached, error: String? = nil) {
        self.directory = directory
        self.snapshot = snapshot
        self.verification = verification
        self.error = error
    }

    public var state: RepositoryState {
        if error != nil { return .error }
        if case .failed = verification { return .error }
        guard let snapshot else { return .error }
        if snapshot.isUnborn { return .unborn }
        if snapshot.isDetached { return .detached }
        guard snapshot.upstream != nil else { return .noUpstream }
        guard let ahead = snapshot.ahead, let behind = snapshot.behind else { return .missingUpstream }
        if ahead > 0 && behind > 0 { return .diverged }
        if ahead > 0 { return .ahead }
        if behind > 0 { return .behind }
        return .inSync
    }

    public var needsPush: Bool {
        guard state != .error, let snapshot else { return false }
        return (snapshot.ahead ?? 0) > 0
    }
}
