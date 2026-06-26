use std::{fs, path::PathBuf};

fn main() {
    let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").expect("manifest dir"));
    let desktop_dir = manifest_dir.parent().expect("desktop dir");
    let index_path = desktop_dir.join("index.html");
    let styles_path = desktop_dir.join("src").join("styles.css");
    let runtime_path = desktop_dir.join("src").join("runtime.js");
    let dist_dir = desktop_dir.join("dist");
    let dist_index_path = dist_dir.join("index.html");

    println!("cargo:rerun-if-changed={}", index_path.display());
    println!("cargo:rerun-if-changed={}", styles_path.display());
    println!("cargo:rerun-if-changed={}", runtime_path.display());

    let index = fs::read_to_string(&index_path).expect("read desktop index.html");
    let styles = fs::read_to_string(&styles_path).expect("read desktop styles.css");
    let runtime = fs::read_to_string(&runtime_path).expect("read desktop runtime.js");

    let index = index.replace(
        r#"<link rel="stylesheet" href="/src/styles.css">"#,
        &format!("<style>\n{styles}\n</style>"),
    );
    let index = index.replace(
        r#"<script src="/src/runtime.js"></script>"#,
        &format!("<script>\n{runtime}\n</script>"),
    );

    fs::create_dir_all(&dist_dir).expect("create desktop dist dir");
    fs::write(dist_index_path, index).expect("write inlined dist index");

    tauri_build::build()
}
