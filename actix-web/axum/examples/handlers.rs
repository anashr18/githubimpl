use async_trait::async_trait;
use axum::{FromRequest, Handler};
use http::Error;
use hyper::body::to_bytes;
use hyper::{Body, Request, Response}; // Replace with actual crate name

// A sample type to extract from the request
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

// Simple handler without FromRequest
async fn hello(_: Request<Body>) -> Result<Response<Body>, Error> {
    Ok(Response::new(Body::from("Hello, world!")))
}

// Handler that uses FromRequest
async fn greet(_req: Request<Body>, user: UserId) -> Result<Response<Body>, Error> {
    Ok(Response::new(Body::from(format!("Hello, {}!", user.0))))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Calling hello handler:");
    let req1 = Request::new(Body::empty());
    let res1 = hello.call(req1).await?;
    let body1 = to_bytes(res1.into_body()).await?;
    println!("{}", std::str::from_utf8(&body1)?);

    println!("\nCalling greet handler:");
    let req2 = Request::builder()
        .header("x-user-id", "anand123")
        .body(Body::empty())?;
    let res2 = greet.call(req2).await?;
    let body2 = to_bytes(res2.into_body()).await?;
    println!("{}", std::str::from_utf8(&body2)?);

    Ok(())
}
