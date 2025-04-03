extern crate actix_http;
use actix_http::server::HttpServer;

fn main() {
    let server = HttpServer::new();
    server.run(); // should print: "Server would start here..."
}
