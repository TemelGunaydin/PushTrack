import Foundation
import Testing
@testable import PushTrackCore

struct StatusAndRenderingTests {
    @Test(arguments: [(0, 0, RepositoryState.inSync), (2, 0, .ahead), (0, 3, .behind), (2, 3, .diverged)])
    func aheadBehindClassification(ahead: Int, behind: Int, expected: RepositoryState) throws {
        let snapshot = try GitSnapshot.parse("# branch.oid abc\0# branch.head main\0# branch.upstream origin/main\0# branch.ab +\(ahead) -\(behind)\0")
        let report = RepositoryReport(directory: URL(fileURLWithPath: "/tmp/repo"), snapshot: snapshot)
        #expect(report.state == expected)
    }

    @Test(arguments: ["", "# branch.head main\0", "# branch.oid abc\0# branch.head main\0# branch.ab not counts\0"])
    func invalidStatusIsNotMistakenForClean(status: String) {
        #expect(throws: PushTrackError.self) { try GitSnapshot.parse(status) }
    }

    @Test func plainAndNarrowOutputRetainMeaningAndSanitizeControls() throws {
        let snapshot = try GitSnapshot.parse("# branch.oid abc\0# branch.head main\0# branch.upstream origin/main\0# branch.ab +2 -0\0? file.txt\0")
        let report = RepositoryReport(directory: URL(fileURLWithPath: "/tmp/evil\u{1B}[2J\nrepo"), snapshot: snapshot)
        for width in [60, 120] {
            let output = TerminalRenderer(color: false, width: width).render(reports: [report], warnings: [], fetch: false, watch: false)
            #expect(output.contains("\u{1B}") == false)
            #expect(output.contains("↑ 2 push bekliyor"))
            #expect(output.contains("?:1"))
            #expect(output.contains("remote doğrulanmadı"))
            #expect(output.contains("origin/main"))
        }
        let colored = TerminalRenderer(color: true).render(reports: [report], warnings: [], fetch: false, watch: true)
        #expect(colored.contains("\u{1B}[33m"))
        #expect(colored.contains("Ctrl+C"))
    }

    @Test func noUpstreamAndMissingUpstreamAreNotGreen() throws {
        let base = "# branch.oid abc\0# branch.head main\0"
        let noUpstream = RepositoryReport(directory: URL(fileURLWithPath: "/tmp/repo"), snapshot: try GitSnapshot.parse(base))
        let missing = RepositoryReport(directory: noUpstream.directory, snapshot: try GitSnapshot.parse(base + "# branch.upstream origin/main\0"))
        #expect(noUpstream.state == .noUpstream)
        #expect(missing.state == .missingUpstream)
    }
}
