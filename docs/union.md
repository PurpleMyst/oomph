# Unions

Consider this Oomph code:

    func foo(Str | null message):
        if message == null:
            print("No message")
        else:
            print(message.get())

    export func main():
        foo(null)       # prints "No message"
        foo("hello")    # prints "hello"

Let's go through this step by step.

    func foo(Str | null message):

Here `Str | null` is a union type. Read it as "`Str` or `null`".

When the code runs, each instance of the union type can be only one of the given types,
in this case, `Str` or `null`.
This type, whichever it is, is called the **active member** of the union.
When this function is called with the string `"hello"` as an argument,
the active member is `Str`.

    if message == null:
        print("No message")

In this context, `null` has a different meaning than previously.
Oomph has two different meanings for `null`:
there's a variable named `null` which we are using here,
and a type named `null` that we used previously.

In this line, the left side of `==` has type `Str | null` and the right side has type `null`.
This causes the `==` operator to [convert](implicit-conversions.md) `null` to type `Str | null`.

Two objects with union types are equal when they have the same active member
and the underlying values are equal.
This ensures that `message == null` is a valid way to check
whether `null` is the active member of `message`.

    else:
        print(message.get())

Recall that `message` has type `Str | null`.
However, when the `else` runs, the active member of `message` can't be `null`.
The `.get()` method converts from `Str | null` to `Str`.

    export func main():
        foo(null)       # prints "No message"
        foo("hello")    # prints hello

Here `null` and `"hello"` have types `null` and `Str` respectively,
but they are [implicitly converted](implicit-conversions.md) to type `Str | null`.


## Multiple types

A union type can have more than two member types, such as `Str | Int | Bool`.
That's not same as `(Str | Int) | Bool`,
where the union type `Str | Int` is inside another union type.


## As

Only unions like `SomeType | null` have a `.get()` method;
other unions don't have it.
To access the `Int` of `Str | Int`, knowing that's the active member, you can use `as`:

    func blah(Str | Int thing):
        print((thing as Int) + 1)

    export func main():
        blah(123)       # prints "124"
        blah("lol")     # runtime error

In fact, `message.get()` in the first example is a shorthand for `message as Str`,
and that too gives a runtime error if called with the wrong active member:

    func greet(Str | null name):
        print("Hello " + name.get())

    export func main():
        greet("World")  # prints "Hello World"
        greet(null)     # runtime error


## Switch

For union types like `SomeType | null`, you can use `== null` and `.get()`.
For other unions, you can use `as`, but that fails at runtime
if the active member isn't what you specified.
To also check which member is active, use `switch`:

    func bar(Int | Bool thing):
        switch thing:
            case Int i:
                print("Got integer: {i}")
            case Bool b:
                print("Got boolean: {b}")

    export func main():
        bar(123)        # prints "Got integer: 123"
        bar(true)       # prints "Got boolean: true"
        bar(false)      # prints "Got boolean: false"

Inside `case Int i`, the variable `i` has type `Int`.
Of course, the type of `thing` doesn't change; it remains as `Int | Bool`.

It is an error if the `thing` of `switch thing` does not have union type.
Also, it is an error if you forget a type in the switch:

    func this_doesnt_compile(Int | Bool | Str thing):
        switch thing:
            case Int i:
                print("Got integer: {i}")

If this isn't what you want, you can use `case *`, which matches all remaining types:

    func this_works(Int | Bool | Str thing):
        switch thing:
            case Int i:
                print("Got integer: {i}")
            case *:
                print("Got something else than an integer")

    export func main():
        this_works(123)     # prints "Got integer: 123"
        this_works("lol")   # prints "Got something else than an integer"


## Typedef

If you want to define a type `Thing` that can be either a `FooThing` or a `BarThing`,
you can do this:

    class FooThing()
    class BarThing()
    typedef Thing = FooThing | BarThing

Now `Thing` can be used as a type, and it means same as `FooThing | BarThing`.

A `typedef` doesn't create a new type; it just gives a new name to an existing type.
This concept is called type aliasing in some programming languages.

If you want, you can also put the `typedef` before the classes (explained in detail
[here](syntax.md#order-of-toplevel-declarations)):

    typedef Thing = FooThing | BarThing
    class FooThing()
    class BarThing()

Oomph doesn't have inheritance, and often you can use unions instead.
The above example is similar to making `FooThing` and `BarThing`
inherit from a base class `Thing` in a programming language that has inheritance.


## Converting to union type

Ideally, you would never need to do this, because implicit conversions should handle this.
However, this is not always the case,
see [#120](https://github.com/Akuli/oomph/issues/120) for example.
In those cases, you can use `new` with a union type. After writing

    let foo = new (Int | Str)(123)

the variable `foo` has type `Int | Str`, with `Int` as the active member having value `123`.
This is the usual `new SomeType(argument)`, with `Int | Str` as the type.
Here [implicit conversion rules](implicit-conversions.md) are used
for converting `123` to type `Int | Str`.
