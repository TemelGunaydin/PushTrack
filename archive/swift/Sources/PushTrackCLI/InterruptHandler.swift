import Foundation
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

/// Mutable signal state is protected by the lock, including reads from GitRunner.
final class InterruptState: @unchecked Sendable {
    private let lock = NSLock()
    private var signalNumber: Int32 = 0

    var receivedSignal: Int32 {
        lock.lock()
        defer { lock.unlock() }
        return signalNumber
    }

    func receive(_ number: Int32) {
        lock.lock()
        defer { lock.unlock() }
        if signalNumber == 0 { signalNumber = number }
    }
}

/// Dispatch handles signals outside the raw POSIX signal handler, where locks
/// are safe. The CLI remains synchronous and can clean up its active subprocess.
final class InterruptHandler {
    let state = InterruptState()
    private var sources: [any DispatchSourceSignal] = []

    init() {
        for number in [SIGINT, SIGTERM] {
            signal(number, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: number, queue: .global())
            source.setEventHandler { [state] in state.receive(number) }
            source.resume()
            sources.append(source)
        }
    }

    deinit {
        for source in sources { source.cancel() }
        signal(SIGINT, SIG_DFL)
        signal(SIGTERM, SIG_DFL)
    }
}
