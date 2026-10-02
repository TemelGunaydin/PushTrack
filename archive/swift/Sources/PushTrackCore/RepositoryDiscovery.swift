import Foundation

public struct RepositoryDiscovery {
    public struct Result {
        public var repositories: [URL] = []
        public var warnings: [String] = []
    }

    public init() {}

    public func discover(in roots: [URL]) -> Result {
        let manager = FileManager.default
        let ignored: Set<String> = ["node_modules", "vendor", "build", "dist", "DerivedData", "Pods", "target"]
        var result = Result()
        var visited = Set<String>()
        var repositories = Set<URL>()

        func visit(_ url: URL, depth: Int) {
            let url = url.standardizedFileURL.resolvingSymlinksInPath()
            // Keep the greatest remaining depth when roots overlap.
            let visitKey = "\(url.path):\(depth)"
            guard visited.insert(visitKey).inserted else { return }
            var isDirectory: ObjCBool = false
            guard manager.fileExists(atPath: url.path, isDirectory: &isDirectory), isDirectory.boolValue else {
                result.warnings.append("Folder not found: \(url.path)")
                return
            }
            if manager.fileExists(atPath: url.appendingPathComponent(".git").path) {
                repositories.insert(url)
                return
            }
            guard depth < 2 else { return }
            do {
                let children = try manager.contentsOfDirectory(
                    at: url, includingPropertiesForKeys: [.isDirectoryKey, .isSymbolicLinkKey],
                    options: [.skipsHiddenFiles]
                )
                for child in children.sorted(by: { $0.path < $1.path }) where !ignored.contains(child.lastPathComponent) {
                    let values = try child.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey])
                    if values.isDirectory == true && values.isSymbolicLink != true {
                        visit(child, depth: depth + 1)
                    }
                }
            } catch {
                result.warnings.append("Could not read folder: \(url.path) — \(error.localizedDescription)")
            }
        }

        for root in roots { visit(root, depth: 0) }
        result.repositories = repositories.sorted { $0.path < $1.path }
        result.warnings = Array(Set(result.warnings)).sorted()
        return result
    }
}
