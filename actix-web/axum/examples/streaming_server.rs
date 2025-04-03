// use bytes::Bytes;
// use http::{Request, Response, StatusCode};
// use hyper::Body;
// use std::{convert::Infallible, net::SocketAddr};
// use tokio::fs::File;
// use tokio_util::io::ReaderStream;
// use tower::ServiceBuilder;

// use axum::Handler;

// async fn stream_file_handler(_req: Request<Body>) -> Result<Response<Body>, Error> {
//     let file = File::open("Cargo.toml").await?; // Change to a large file if needed
//     let stream = ReaderStream::new(file);
//     let body = Body::wrap_stream(stream);

//     let response = Response::builder()
//         .status(StatusCode::OK)
//         .header("Content-Type", "text/plain")
//         .body(body)?;

//     Ok(response)
// }

// #[tokio::main]
// async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
//     let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
//     println!("Listening on http://{}", addr);

//     // Wrap the handler in a tower-compatible service
//     let make_service = tower::service_fn(|req: Request<Body>| async move {
//         // Delegate to our framework’s call method
//         stream_file_handler.call(req).await.map_err(|e| {
//             eprintln!("Internal error: {}", e);
//             Infallible
//         })
//     });

//     hyper::Server::bind(&addr).serve(make_service).await?;

//     Ok(())
// }
