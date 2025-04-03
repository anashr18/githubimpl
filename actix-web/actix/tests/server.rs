extern crate actix_http;

use actix_http::HttpServer;

#[test]
fn test_server_bootstrap() {
    let server = HttpServer::new();
    server.run(); // should just print to stdout
}
