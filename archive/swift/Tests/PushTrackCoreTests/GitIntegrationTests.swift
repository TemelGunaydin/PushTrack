import Foundation
import Testing
@testable import PushTrackCore

private struct GitFixture {
    let root: URL
    let local: URL
    let remote: URL
    let git = GitRunner()

    init() throws {
        root = FileManager.default.temporaryDirectory.appendingPathComponent("pushtrack-tests-\(UUID().uuidString)").resolvingSymlinksInPath()
        local = root.appendingPathComponent("local project")
        remote = root.appendingPathComponent("remote.git")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        _ = try git.checked(["init", "--initial-branch=main", local.path], at: root)
        try configure(local)
    }

    func cleanUp() { try? FileManager.default.removeItem(at: root) }

    func configure(_ directory: URL) throws {
        for (key, value) in [
            ("user.name", "PushTrack Tests"), ("user.email", "tests@example.invalid"),
            ("commit.gpgsign", "false"), ("core.hooksPath", "/dev/null"),
        ] {
            _ = try git.checked(["config", key, value], at: directory)
        }
    }

    func commit(_ name: String, content: String = UUID().uuidString, at directory: URL? = nil) throws {
        let directory = directory ?? local
        try Data(content.utf8).write(to: directory.appendingPathComponent(name))
        _ = try git.checked(["add", "--", name], at: directory)
        _ = try git.checked(["commit", "-m", "Test commit"], at: directory)
    }

    func setUpRemote() throws {
        try commit("initial.txt", content: "initial\n")
        _ = try git.checked(["init", "--bare", "--initial-branch=main", remote.path], at: root)
        _ = try git.checked(["remote", "add", "origin", remote.path], at: local)
        _ = try git.checked(["push", "-u", "origin", "main"], at: local)
    }

    func peer() throws -> URL {
        let peer = root.appendingPathComponent("peer")
        _ = try git.checked(["clone", remote.path, peer.path], at: root)
        try configure(peer)
        return peer
    }
}

struct GitIntegrationTests {
    let inspector = RepositoryInspector()

    @Test func unbornUntrackedNoUpstreamAheadAndPushedLifecycle() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        #expect(inspector.inspect(fixture.local, fetch: false).state == .unborn)
        try fixture.commit("first.txt")
        #expect(inspector.inspect(fixture.local, fetch: true).state == .noUpstream)
        try fixture.setUpRemote()
        #expect(inspector.inspect(fixture.local, fetch: false).state == .inSync)
        try fixture.commit("not-pushed.txt")
        let pending = inspector.inspect(fixture.local, fetch: true)
        #expect(pending.state == .ahead)
        #expect(pending.snapshot?.ahead == 1)
        #expect(pending.needsPush)
        if case .fetched = pending.verification {} else { Issue.record("Fetch should be verified") }
        _ = try fixture.git.checked(["push", "origin", "main"], at: fixture.local)
        #expect(inspector.inspect(fixture.local, fetch: true).state == .inSync)
    }

    @Test func staleCacheBecomesBehindThenDivergedWithoutChangingWorkingTree() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.setUpRemote()
        let peer = try fixture.peer()
        try fixture.commit("remote-change.txt", at: peer)
        _ = try fixture.git.checked(["push", "origin", "main"], at: peer)
        #expect(inspector.inspect(fixture.local, fetch: false).state == .inSync, "Cached refs can be stale")
        let behind = inspector.inspect(fixture.local, fetch: true)
        #expect(behind.state == .behind)
        #expect(behind.snapshot?.behind == 1)
        try fixture.commit("local-change.txt")
        let uncommitted = fixture.local.appendingPathComponent("uncommitted.txt")
        let data = Data("do not change".utf8)
        try data.write(to: uncommitted)
        let head = try fixture.git.checked(["rev-parse", "HEAD"], at: fixture.local)
        let indexURL = fixture.local.appendingPathComponent(".git/index")
        let index = try Data(contentsOf: indexURL)
        let remoteHead = try fixture.git.checked(["rev-parse", "HEAD"], at: fixture.remote)
        let report = inspector.inspect(fixture.local, fetch: true)
        #expect(report.state == .diverged)
        #expect(report.snapshot?.ahead == 1)
        #expect(report.snapshot?.behind == 1)
        #expect(report.snapshot?.untracked == 1)
        #expect(try Data(contentsOf: uncommitted) == data)
        #expect(try Data(contentsOf: indexURL) == index)
        #expect(try fixture.git.checked(["rev-parse", "HEAD"], at: fixture.local) == head)
        #expect(try fixture.git.checked(["rev-parse", "HEAD"], at: fixture.remote) == remoteHead)
    }

    @Test func deletedRemoteBranchIsNotReportedAsVerified() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.setUpRemote()
        _ = try fixture.git.checked(["update-ref", "-d", "refs/heads/main"], at: fixture.remote)
        #expect(inspector.inspect(fixture.local, fetch: false).state == .inSync)
        let failed = inspector.inspect(fixture.local, fetch: true)
        #expect(failed.state == .error)
        if case .failed = failed.verification {} else { Issue.record("Deleted remote branch must fail verification") }
    }

    @Test func missingTrackingRefCanBeRestoredByFetch() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.setUpRemote()
        _ = try fixture.git.checked(["update-ref", "-d", "refs/remotes/origin/main"], at: fixture.local)
        #expect(inspector.inspect(fixture.local, fetch: false).state == .missingUpstream)
        #expect(inspector.inspect(fixture.local, fetch: true).state == .inSync)
    }

    @Test func fetchDoesNotUpdateLocalBranchesThroughCustomRefmaps() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.setUpRemote()
        _ = try fixture.git.checked(["branch", "protected"], at: fixture.local)
        let protectedHead = try fixture.git.checked(["rev-parse", "protected"], at: fixture.local)
        _ = try fixture.git.checked(["config", "--add", "remote.origin.fetch", "+refs/heads/main:refs/heads/protected"], at: fixture.local)
        let peer = try fixture.peer()
        try fixture.commit("peer-update.txt", at: peer)
        _ = try fixture.git.checked(["push", "origin", "main"], at: peer)
        #expect(inspector.inspect(fixture.local, fetch: true).state == .behind)
        #expect(try fixture.git.checked(["rev-parse", "protected"], at: fixture.local) == protectedHead)
    }

    @Test func unavailableRemoteCannotProduceGreenStatus() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.setUpRemote()
        _ = try fixture.git.checked(["remote", "set-url", "origin", fixture.root.appendingPathComponent("missing.git").path], at: fixture.local)
        let failed = inspector.inspect(fixture.local, fetch: true)
        #expect(failed.state == .error)
        let output = TerminalRenderer(color: true).render(reports: [failed], warnings: [], fetch: true, watch: false)
        #expect(output.contains("\u{1B}[32m") == false)
        #expect(output.contains("remote doğrulanamadı"))
    }

    @Test func countsStagedUnstagedUntrackedAndRenameWithTrickyPaths() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        let original = "? looks-untracked\nold.txt"
        try fixture.commit(original, content: "rename me\n")
        try fixture.commit("modified.txt", content: "before\n")
        _ = try fixture.git.checked(["mv", "--", original, "renamed.txt"], at: fixture.local)
        try Data("after\n".utf8).write(to: fixture.local.appendingPathComponent("modified.txt"))
        try Data("new\n".utf8).write(to: fixture.local.appendingPathComponent("new\nfile.txt"))
        let snapshot = try #require(inspector.inspect(fixture.local, fetch: false).snapshot)
        #expect(snapshot.staged == 1)
        #expect(snapshot.unstaged == 1)
        #expect(snapshot.untracked == 1)
        #expect(snapshot.changedFiles == 3)
        #expect(snapshot.branch == "main")
    }

    @Test func detachedAndLocalUpstreamRemainExplicit() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.commit("file.txt")
        _ = try fixture.git.checked(["branch", "other"], at: fixture.local)
        _ = try fixture.git.checked(["branch", "--set-upstream-to=other"], at: fixture.local)
        let local = inspector.inspect(fixture.local, fetch: true)
        #expect(local.state == .inSync)
        if case .localUpstream = local.verification {} else { Issue.record("Local tracking is not a remote fetch") }
        _ = try fixture.git.checked(["checkout", "--detach"], at: fixture.local)
        #expect(inspector.inspect(fixture.local, fetch: true).state == .detached)
    }

    @Test func repositorySSHConfigurationIsPreservedWithoutInteractivePrompts() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.setUpRemote()
        let helper = fixture.root.appendingPathComponent("fake-ssh.sh")
        try Data("printf '%s' \"$SSH_ASKPASS_REQUIRE\" > ssh-used\nexit 1\n".utf8).write(to: helper)
        _ = try fixture.git.checked(["config", "core.sshCommand", "sh '\(helper.path)'"], at: fixture.local)
        _ = try fixture.git.checked(["remote", "set-url", "origin", "ssh://127.0.0.1:1/repo"], at: fixture.local)
        #expect(inspector.inspect(fixture.local, fetch: true).state == .error)
        let marker = try String(contentsOf: fixture.local.appendingPathComponent("ssh-used"), encoding: .utf8)
        #expect(marker == "force")
    }

    @Test func mergeConflictsAreCounted() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.commit("conflict.txt", content: "base\n")
        _ = try fixture.git.checked(["checkout", "-b", "feature"], at: fixture.local)
        try fixture.commit("conflict.txt", content: "feature\n")
        _ = try fixture.git.checked(["checkout", "main"], at: fixture.local)
        try fixture.commit("conflict.txt", content: "main\n")
        let merge = try fixture.git.run(["merge", "feature"], at: fixture.local)
        #expect(merge.status != 0)
        let report = inspector.inspect(fixture.local, fetch: false)
        #expect(report.snapshot?.conflicts == 1)
        let output = TerminalRenderer(color: false).render(reports: [report], warnings: [], fetch: false, watch: false)
        #expect(output.contains("U:1"))
    }

    @Test func discoverySupportsWorktreesOverlappingRootsAndMissingFolders() throws {
        let fixture = try GitFixture()
        defer { fixture.cleanUp() }
        try fixture.commit("first.txt")
        let worktree = fixture.root.appendingPathComponent("worktree")
        _ = try fixture.git.checked(["worktree", "add", "-b", "feature", worktree.path], at: fixture.local)
        let missing = fixture.root.appendingPathComponent("gone")
        let result = RepositoryDiscovery().discover(in: [fixture.root, fixture.local, worktree, missing])
        #expect(Set(result.repositories.map(\.path)) == Set([fixture.local.path, worktree.path]))
        #expect(result.warnings.count == 1)
        #expect(inspector.inspect(worktree, fetch: false).snapshot?.branch == "feature")
    }
}
