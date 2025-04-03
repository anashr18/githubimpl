use async_trait::async_trait;
use bytes::Bytes;
use futures_util::future::ok;
use http::{Error, Method, Request, Response, StatusCode};
pub use hyper::body::Body;
use std::{future::Future, task::Poll};
use tower::Service;

#[derive(Clone)]
pub struct App<R> {
    router: R,
}

#[derive(Clone, Copy)]
pub struct EmptyRouter(());

impl Service<Request<Body>> for EmptyRouter {
    type Response = Response<Body>;
    type Error = Error;
    type Future = futures_util::future::Ready<Result<Self::Response, Self::Error>>;

    fn poll_ready(
        &mut self,
        _cx: &mut std::task::Context<'_>,
    ) -> std::task::Poll<Result<(), Self::Error>> {
        std::task::Poll::Ready(Ok(()))
    }

    fn call(&mut self, _req: Request<Body>) -> Self::Future {
        let mut res = Response::new(Body::empty());
        *res.status_mut() = StatusCode::NOT_FOUND;
        futures_util::future::ready(Ok(res))
    }
}
// implementing struct concrete App with EmptyRouter
impl App<EmptyRouter> {
    pub fn new() -> Self {
        App {
            router: EmptyRouter(()),
        }
    }
}

impl<R> App<R>
where
    R: Service<Request<Body>, Response = Response<Body>, Error = Error> + Clone + Send + 'static,
    R::Future: Send + 'static,
{
    pub async fn call(&self, req: Request<Body>) -> Result<Response<Body>, Error> {
        let mut svc = self.router.clone();
        svc.call(req).await
    }
}

#[async_trait]
pub trait FromRequest: Sized {
    async fn from_request(req: &mut Request<Body>) -> Self;
}

#[async_trait]
pub trait Handler<Out> {
    async fn call(self, req: Request<Body>) -> Result<Response<Body>, Error>;
}
#[async_trait]
impl<F, Fut> Handler<()> for F
where
    F: Fn(Request<Body>) -> Fut + Send + Sync,
    Fut: Future<Output = Result<Response<Body>, Error>> + Send,
{
    async fn call(self, req: Request<Body>) -> Result<Response<Body>, Error> {
        println!("calling handler with zero extractor");
        let res = self(req).await?;
        Ok(res)
    }
}
#[async_trait]
#[allow(non_snake_case)]
impl<F, Fut, T1> Handler<(T1,)> for F
where
    F: Fn(Request<Body>, T1) -> Fut + Send + Sync,
    Fut: Future<Output = Result<Response<Body>, Error>> + Send,
    T1: FromRequest + Send,
{
    async fn call(self, mut req: Request<Body>) -> Result<Response<Body>, Error> {
        let T1 = T1::from_request(&mut req).await;
        let res = self(req, T1).await?;
        Ok(res)
    }
}

#[async_trait]
#[allow(non_snake_case)]
impl<F, Fut, T1, T2> Handler<(T1, T2)> for F
where
    F: Fn(Request<Body>, T1, T2) -> Fut + Send + Sync,
    Fut: Future<Output = Result<Response<Body>, Error>> + Send,
    T1: FromRequest + Send,
    T2: FromRequest + Send,
{
    async fn call(self, mut req: Request<Body>) -> Result<Response<Body>, Error> {
        let T1 = T1::from_request(&mut req).await;
        let T2 = T2::from_request(&mut req).await;
        let res = self(req, T1, T2).await?;
        Ok(res)
    }
}

#[derive(Clone)]
pub struct Route<H, F> {
    handler: H,
    route_spec: RouteSpec,
    fallback: F,
}
#[derive(Clone)]
struct RouteSpec {
    method: Method,
    spec: Bytes,
}
// This is to validate the uri path as bytes comparisons and method used
impl RouteSpec {
    fn matches<B>(&self, req: &Request<B>) -> bool {
        req.method() == self.method && req.uri().path().as_bytes() == self.spec
    }
}

// impl<H, F> Service<Request<Body>> for Route<H, F>
// where
//     H: Service<Request<Body>, Response = Response<Body>, Error = Error> + Clone + Send + 'static,
//     H::Future: Send,
//     F: Service<Request<Body>, Response = Response<Body>, Error = Error> + Clone + Send + 'static,
//     F::Future: Send,
// {
//     type Response = Response<Body>;
//     type Error = Error;
//     type Future = futures_util::future::BoxFuture<'static, Result<Self::Response, Self::Error>>;
//     fn poll_ready(
//         &mut self,
//         cx: &mut std::task::Context<'_>,
//     ) -> std::task::Poll<Result<(), Self::Error>> {
//         Poll::Ready(Ok(()))
//     }
//     fn call(&mut self, req: Request<Body>) -> Self::Future {
//         if self.route_spec.matches(&req) {}
//     }
// }
