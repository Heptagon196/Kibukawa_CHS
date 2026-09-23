use percent_encoding::percent_decode_str;
use std::{
    fs,
    path::{Component, Path, PathBuf},
};

fn web_root() -> PathBuf {
    let beside_exe = std::env::current_exe()
        .ok()
        .and_then(|path| path.parent().map(|parent| parent.join("www")));

    if let Some(root) = beside_exe.filter(|path| path.is_dir()) {
        root
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../dist")
    }
}

fn content_type(path: &Path) -> &'static str {
    match path.extension().and_then(|value| value.to_str()).unwrap_or("") {
        "html" | "htm" => "text/html; charset=utf-8",
        "css" => "text/css; charset=utf-8",
        "js" | "mjs" => "text/javascript; charset=utf-8",
        "json" => "application/json; charset=utf-8",
        "wasm" => "application/wasm",
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "ico" => "image/x-icon",
        "svg" => "image/svg+xml",
        "mp3" => "audio/mpeg",
        "wav" => "audio/wav",
        "swf" => "application/x-shockwave-flash",
        "zip" => "application/zip",
        _ => "application/octet-stream",
    }
}

fn safe_relative_path(uri_path: &str) -> Option<PathBuf> {
    let decoded = percent_decode_str(uri_path.trim_start_matches('/'))
        .decode_utf8()
        .ok()?;
    let relative = if decoded.is_empty() {
        PathBuf::from("index.html")
    } else {
        PathBuf::from(decoded.as_ref())
    };

    if relative
        .components()
        .all(|part| matches!(part, Component::Normal(_)))
    {
        Some(relative)
    } else {
        None
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let root = web_root();
    tauri::Builder::default()
        .register_uri_scheme_protocol("kibukawa", move |_context, request| {
            let Some(relative) = safe_relative_path(request.uri().path()) else {
                return tauri::http::Response::builder()
                    .status(400)
                    .header("Content-Type", "text/plain; charset=utf-8")
                    .body(b"Invalid path".to_vec())
                    .unwrap();
            };

            let path = root.join(relative);
            match fs::read(&path) {
                Ok(body) => tauri::http::Response::builder()
                    .status(200)
                    .header("Content-Type", content_type(&path))
                    .header("Access-Control-Allow-Origin", "*")
                    .body(body)
                    .unwrap(),
                Err(_) => tauri::http::Response::builder()
                    .status(404)
                    .header("Content-Type", "text/plain; charset=utf-8")
                    .body(b"Not found".to_vec())
                    .unwrap(),
            }
        })
        .run(tauri::generate_context!())
        .expect("failed to run the Kibukawa desktop application");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_normal_and_encoded_paths() {
        assert_eq!(safe_relative_path("/"), Some(PathBuf::from("index.html")));
        assert_eq!(
            safe_relative_path("/games/a%20b/index.html"),
            Some(PathBuf::from("games/a b/index.html"))
        );
    }

    #[test]
    fn rejects_paths_outside_www() {
        assert_eq!(safe_relative_path("/%2e%2e/secret.txt"), None);
        assert_eq!(safe_relative_path("/games/%2e%2e/%2e%2e/secret.txt"), None);
        assert_eq!(safe_relative_path("/C:%5CWindows%5Cwin.ini"), None);
    }
}
