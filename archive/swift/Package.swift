// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "PushTrack",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "pushtrack", targets: ["PushTrackCLI"])],
    targets: [
        .target(name: "PushTrackCore"),
        .executableTarget(name: "PushTrackCLI", dependencies: ["PushTrackCore"]),
        .testTarget(name: "PushTrackCoreTests", dependencies: ["PushTrackCore"]),
    ]
)
