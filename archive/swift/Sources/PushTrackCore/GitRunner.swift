import Foundation
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

public struct GitOutput: Sendable {
    public let status: Int32
    public let stdout: String
    public let stderr: String
}

/// Synchronous, bounded subprocess execution for the CLI. File-backed output
/// avoids pipe deadlocks even for repositories with a large number of changes.
public struct GitRunner: Sendable {
    public var timeout: TimeInterval
    public var isCancelled: @Sendable () -> Bool

    public init(timeout: TimeInterval = 20, isCancelled: @escaping @Sendable () -> Bool = { false }) {
        self.timeout = timeout
        self.isCancelled = isCancelled
    }

    public func run(_ arguments: [String], at directory: URL) throws -> GitOutput {
        if isCancelled() { throw CancellationError() }
        let temporary = FileManager.default.temporaryDirectory.appendingPathComponent("pushtrack-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: false)
        defer { try? FileManager.default.removeItem(at: temporary) }
        let stdoutURL = temporary.appendingPathComponent("stdout")
        let stderrURL = temporary.appendingPathComponent("stderr")
        _ = FileManager.default.createFile(atPath: stdoutURL.path, contents: nil)
        _ = FileManager.default.createFile(atPath: stderrURL.path, contents: nil)
        let stdout = try FileHandle(forWritingTo: stdoutURL)
        defer { try? stdout.close() }
        let stderr = try FileHandle(forWritingTo: stderrURL)
        defer { try? stderr.close() }

        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["git", "-c", "core.fsmonitor=false", "-c", "color.ui=false"] + arguments
        process.currentDirectoryURL = directory
        process.standardInput = FileHandle.nullDevice
        process.standardOutput = stdout
        process.standardError = stderr
        var environment = ProcessInfo.processInfo.environment
        // An invocation from a Git hook must still inspect the requested repository.
        for key in ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"] {
            environment.removeValue(forKey: key)
        }
        environment["LC_ALL"] = "C"
        environment["GIT_OPTIONAL_LOCKS"] = "0"
        environment["GIT_TERMINAL_PROMPT"] = "0"
        environment["GCM_INTERACTIVE"] = "never"
        environment["GIT_ASKPASS"] = "/usr/bin/false"
        environment["SSH_ASKPASS"] = "/usr/bin/false"
        // Prevent OpenSSH from reading a password from /dev/tty without
        // overriding core.sshCommand, GIT_SSH, or GIT_SSH_COMMAND.
        environment["SSH_ASKPASS_REQUIRE"] = "force"
        process.environment = environment
        try process.run()
        let deadline = ProcessInfo.processInfo.systemUptime + timeout
        while process.isRunning {
            let cancelled = isCancelled()
            if cancelled || ProcessInfo.processInfo.systemUptime >= deadline {
                stop(process)
                if cancelled { throw CancellationError() }
                throw PushTrackError("Git operation timed out after \(Int(timeout)) seconds.")
            }
            Thread.sleep(forTimeInterval: 0.005)
        }
        process.waitUntilExit()
        return GitOutput(
            status: process.terminationStatus,
            stdout: String(decoding: try Data(contentsOf: stdoutURL), as: UTF8.self),
            stderr: String(decoding: try Data(contentsOf: stderrURL), as: UTF8.self)
        )
    }

    private func stop(_ process: Process) {
        let pid = process.processIdentifier
        // Foundation normally creates a separate process group. Terminate the
        // whole owned group so SSH and credential helpers do not outlive Git.
        let ownsGroup = getpgid(pid) == pid
        if ownsGroup { kill(-pid, SIGTERM) } else { process.terminate() }
        Thread.sleep(forTimeInterval: 0.1)
        if ownsGroup { kill(-pid, SIGKILL) }
        else if process.isRunning { kill(pid, SIGKILL) }
        process.waitUntilExit()
    }

    public func checked(_ arguments: [String], at directory: URL) throws -> String {
        let output = try run(arguments, at: directory)
        guard output.status == 0 else {
            let reason = output.stderr.trimmingCharacters(in: .whitespacesAndNewlines)
            throw PushTrackError(reason.isEmpty ? "Git operation failed (exit \(output.status))." : reason)
        }
        return output.stdout
    }
}
