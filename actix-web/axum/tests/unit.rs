use axum::{App, Body};
use http::{Request, StatusCode};

#[tokio::test]
async fn test_empty_router_404() {
    let app = App::new();
    let req = Request::new(Body::empty());
    let res = app.call(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::NOT_FOUND);
    // println!("")
}
