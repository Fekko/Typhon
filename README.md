# Typhon
##### Author: Rene Fekkes

Typhon is a command line feedback tool developed to detect type errors and document types for the Python 3 programming language.

![Typhon Logo](logo.png)

## Manual

Requirements:
- Python 3.10

Usage in terminal:
```
python main.py <filename>
```
Usage in VSCode:

Set arguments in launch.json
and run with `Ctrl+F5`

## Examples
### Example 1
```
python main.py resources/example1.py
```

Input:
```python
a = 1
b = 2
a = True

if a:
    c = "hello"
    c = 1
else:
    c = 2.0
```

Expected output:
```python
a: int = 1
b: int = 2
a: bool = True

if a:
    c: str = "hello"
    c: int = 1
else:
    c: float = 2.0
```

### Example 2
```
python main.py resources/example2.py
```

Input:
```python
def function():
    if True:
        return 3
    return 1.5

result = function()
```

Expected output:
```python
def function()->int|float:
    if True:
        return 3
    return 1.5
    
result: int|float = function()
```

### Example 3
```
python main.py resources/example3.py
```

Input:
```python
def id(a):
    return a

result = id(id(id(id(12))))
```

Expected output:
```python
def id(a: T) -> T:
    return a

result: int = id(id(id(id(12))))
```

### Example 4
```
python main.py resources/example4.py
```

Input:
```python
def select(cond, val1, val2):
    if cond:
        return val1
    return val2

result = select(True, 1, "hello")
```

Expected output:
```python
def select(cond: T_0|bool, val1: T_1, val2: T_2)->T_1|T_2:
    if cond:
        return val1
    return val2
    
result: str|int = select(True, 1, "hello")
```

## Description

Tyhpon is a combination of the words "Typed Python".
The tool supports Python by enforcing a static typesystem.
Not only does this system report all types errors, it is also able to do this at compile time.
This is achieved by using type inference, a process whereby types are automatically deduced.

Typhon's type system is heavily based on Dolan and Mycroft's work:
- Polymorphism, Subtyping, and Type Inference in MLsub
- Algebraic Subtyping

However, the tool has been written for students.
Not all features are supported such as classes, exceptions and comprehensions.
Also this is the first version of Typhon, it still is a prototype.
Not all Python built-ins are supported. 
The typesystem also restricts the usage of Python:
- All objects are immutable
- Functions only work with pass by value
- Reassignment isn't allowed: a new variable is introduced that shadows the previous one
- Functions cannot change global variables
- Global variables cannot influence functions after they are defined.

The tool has also been evaluated.
90% of program's of a dataset from a course introductory programming were unsupported.
A lot of extra features should be included before the Typhon becomes practically applicable.
Also, Typhon reports in 50% of the supported programs a type error.
This is due to the strict nature of the tool.
Further work is needed to resolve these issues. 


## About

This project was developed for my thesis called "type inferentie for Python" to achieve the degree master in computerscience at KULeuven.
Note that it has been written in Dutch.
