# actix-http

Syntax	Meaning	Common Use
*x	Dereference	Access value from pointer
&x	Reference	Borrow value
*&x	Borrow then dereference	Often useless manually
&*x	Deref then borrow	Access inner data in smart pointers
**x	Double deref	Deeply nested pointers
*foo.get_mut()	Assign to returned ref	Modify internals via mutable methods

let maybe_name: Option<String> = Some("Anand".to_string());
// Use .as_ref() to borrow the inner value instead of moving it
if let Some(name_ref) = maybe_name.as_ref() {
    println!("Length: {}", name_ref.len()); // name_ref: &String
}
// maybe_name is still usable here



let res: Result<String, String> = Ok("Hello".to_string());
match res.as_ref() {
    Ok(val) => println!("Ok with val = {}", val), // val: &String
    Err(err) => println!("Error = {}", err),
}

use std::collections::HashMap;

fn main() {
    let mut map = HashMap::new();
    map.insert("apple", 3);
    map.insert("banana", 5);

    let maybe_val: Option<&i32> = map.get("apple"); // Option<&i32>
    
    // Use as_ref() to borrow without moving
    if let Some(count_ref) = maybe_val.as_ref() {
        println!("Count of apples: {}", count_ref);
    }

    // Result example
    let parsed: Result<i32, _> = "42".parse();

    match parsed.as_ref() {
        Ok(num_ref) => println!("Parsed number: {}", num_ref),
        Err(e) => println!("Parse failed: {}", e),
    }

    // Option<String> vs Option<&String>
    let name: Option<String> = Some("Anand".to_string());

    if let Some(name_ref) = name.as_ref() {
        println!("Name length: {}", name_ref.len());
    }

    println!("Still have name: {:?}", name);
}

Just remember:
if let is concise but ignores the other case
match forces complete handling

So? Operator should be used when we need to capture the error in the output. If you just want to continue with the success value, we shouldn't be using the? For example, with options, we can use if let some and with results, we can fetch okay value. In cases of option and result, we can just ignore the field values but program still continues.


What is object safety?
A trait is object-safe if it can be turned into a trait object — that is, you can use dyn Trait.

For a trait to be object-safe, it must follow these rules:

✅ Methods must not return Self

✅ Methods must not use generic parameters (like fn foo<T>())

✅ All methods must take &self, &mut self, or self as their first argument

✅ Associated types can be okay if not used in signatures in object-unsafe ways

❌ No async fn (unless using special workarounds like async_trait)

