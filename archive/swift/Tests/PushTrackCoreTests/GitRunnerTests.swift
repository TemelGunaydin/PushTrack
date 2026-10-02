import Foundation
import Testing
@testable import PushTrackCore
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

struct GitRunnerTests {
    @Test func cancellationDoesNotLaunchGit() {
        let git = GitRunner(isCancelled: { true })
        #expect(throws: CancellationError.self) {
            try git.run(["--version"], at: URL(fileURLWithPath: "/path/does/not/exist"))
        }
    }

    @Test func timeoutTerminatesGitAndItsHelper() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let git = GitRunner(timeout: 0.3)
        #expect(throws: PushTrackError.self) {
            try git.run(["-c", "alias.waiter=!sleep 30 & echo $! > child.pid; wait", "waiter"], at: directory)
        }
        let pidText = try String(contentsOf: directory.appendingPathComponent("child.pid"), encoding: .utf8)
        let pid = try #require(Int32(pidText.trimmingCharacters(in: .whitespacesAndNewlines)))
        defer { if kill(pid, 0) == 0 { kill(pid, SIGKILL) } }
        let deadline = ProcessInfo.processInfo.systemUptime + 2
        while kill(pid, 0) == 0 && ProcessInfo.processInfo.systemUptime < deadline {
            Thread.sleep(forTimeInterval: 0.01)
        }
        #expect(kill(pid, 0) == -1, "Git helper should not outlive the timed-out command")
    }

    @Test func largeOutputDoesNotDeadlock() throws {
        let output = try GitRunner().checked([
            "-c", "alias.output=!yes x | head -c 200000", "output",
        ], at: FileManager.default.temporaryDirectory)
        #expect(output.utf8.count == 200_000)
    }
}
