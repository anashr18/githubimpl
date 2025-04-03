use async_trait::async_trait;
use axum::{Body, FromRequest, Handler};
use http::{Error, Request, Response};
use hyper::body::to_bytes;

async fn hello(_req: Request<Body>) -> Result<Response<Body>, Error> {
    Ok(Response::new(Body::from("Hello from hello handler")))
}

pub struct UserId(pub String);

#[async_trait]
impl FromRequest for UserId {
    async fn from_request(req: &mut Request<Body>) -> Self {
        let user_id = req
            .headers()
            .get("x-user-id")
            .and_then(|h| h.to_str().ok())
            .unwrap_or("guest")
            .to_string();

        UserId(user_id)
    }
}

async fn hello_with_extractor(_req: Request<Body>, user: UserId) -> Result<Response<Body>, Error> {
    Ok(Response::new(Body::from(format!(
        "Hello from hello with extractor handler {}",
        user.0
    ))))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let req = Request::new(Body::empty());
    let res = hello.call(req).await?;
    let body = to_bytes(res.into_body()).await?;
    println!(
        "{:?}",
        std::str::from_utf8(&body).expect("Not a valid utf-8")
    );
    let req1 = Request::builder()
        .header("x-user-id", "ElonMusk")
        .body(Body::empty())?;
    let res1 = hello_with_extractor.call(req1).await?;
    let body1 = to_bytes(res1.into_body()).await?;
    println!(
        "{:?}",
        std::str::from_utf8(&body1).expect("Not a valid utf-8")
    );
    Ok(())
}
