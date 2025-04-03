use axum::{App, Body};
use http::{Request, StatusCode};

#[tokio::main]
async fn main() {
    let app = App::new();
    let req = Request::new(Body::empty());
    let response = app.call(req).await.unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
    println!("Response came from router:: {}", response.status());
}
