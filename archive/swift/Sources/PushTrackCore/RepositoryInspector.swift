import Foundation

public struct RepositoryInspector {
    public var git: GitRunner

    public init(git: GitRunner = GitRunner()) { self.git = git }

    public func inspect(_ directory: URL, fetch: Bool) -> RepositoryReport {
        do {
            let initial = try snapshot(at: directory)
            var report = RepositoryReport(directory: directory, snapshot: initial)
            guard fetch, !initial.isDetached, !initial.isUnborn else { return report }
            do {
                let tracking = try tracking(for: initial.branch, at: directory)
                guard !tracking.upstream.isEmpty else {
                    report.verification = .notApplicable
                    return report
                }
                guard tracking.remote != "." else {
                    report.verification = .localUpstream
                    return report
                }
                // Only write a remote-tracking ref, never a local branch or tag.
                guard tracking.upstream.hasPrefix("refs/remotes/"),
                      tracking.remoteRef.hasPrefix("refs/"), !tracking.remote.isEmpty else {
                    throw PushTrackError("Upstream is not a safe remote-tracking ref; fetch was skipped.")
                }
                _ = try git.checked([
                    "fetch", "--quiet", "--no-tags", "--no-write-fetch-head",
                    "--no-recurse-submodules", "--no-auto-maintenance", "--refmap=", "--",
                    tracking.remote, "+\(tracking.remoteRef):\(tracking.upstream)",
                ], at: directory)
                let checkedAt = Date()
                let updated = try snapshot(at: directory)
                report.snapshot = updated
                guard initial.branch == updated.branch,
                      tracking == (try self.tracking(for: updated.branch, at: directory)) else {
                    throw PushTrackError("The branch or upstream changed during the check. Please refresh.")
                }
                report.verification = .fetched(checkedAt)
            } catch {
                // A failed network check must never be rendered as a verified green state.
                report.verification = .failed(error.localizedDescription)
            }
            return report
        } catch {
            return RepositoryReport(directory: directory, error: error.localizedDescription)
        }
    }

    private func snapshot(at directory: URL) throws -> GitSnapshot {
        try GitSnapshot.parse(git.checked([
            "status", "--porcelain=v2", "--branch", "--untracked-files=all", "-z",
        ], at: directory))
    }

    private struct Tracking: Equatable {
        let upstream: String
        let remote: String
        let remoteRef: String
    }

    private func tracking(for branch: String, at directory: URL) throws -> Tracking {
        let output = try git.checked([
            "for-each-ref", "--format=%(upstream)%00%(upstream:remotename)%00%(upstream:remoteref)",
            "refs/heads/\(branch)",
        ], at: directory).trimmingCharacters(in: .newlines)
        let fields = output.split(separator: "\0", omittingEmptySubsequences: false)
        guard fields.count == 3 else {
            throw PushTrackError("Could not read upstream configuration.")
        }
        return Tracking(upstream: String(fields[0]), remote: String(fields[1]), remoteRef: String(fields[2]))
    }
}
