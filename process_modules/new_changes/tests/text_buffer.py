from process_modules.text_buffer import Textbuffer
from process_modules.new_changes.text_buffer import TextBuffer




def test():
    text_buffer_1 = TextBuffer()
    text_buffer_2 = Textbuffer()
    print("Test 1")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("Test 1")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")



    text_buffer_1.all_clear()
    text_buffer_2.all_clear()
    print("Test 2")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("Test 2")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")


    text_buffer_1.update_buffer("hello")
    text_buffer_2.update_buffer("hello")
    print("Test 3")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("input 1: hello")
        print("input 2: hello")
        print("Test 3")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")


    text_buffer_1.update_buffer("hello")
    text_buffer_2.update_buffer("hello")
    print("Test 4")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("input 1: hello")
        print("input 2: hello")
        print("Test 4")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")


    text_buffer_1.update_buffer("nav_d")
    text_buffer_2.update_buffer("nav_d")
    print("Test 5")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("input 1: hello")
        print("input 2: hello")
        print("Test 5")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")
    if(text_buffer_1.buffer_cursor != text_buffer_2.menu_buffer_cursor):
        print(f"result: {text_buffer_1.buffer_cursor}")
        print(f"expected: {text_buffer_2.menu_buffer_cursor}")

    text_buffer_1.update_buffer("nav_b")
    text_buffer_2.update_buffer("nav_b")
    print("Test 6")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("Test 6")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")
        print(f"result: {text_buffer_1.buffer_cursor}")
        print(f"expected: {text_buffer_2.menu_buffer_cursor}")
    
    if(text_buffer_1.buffer_cursor != text_buffer_2.menu_buffer_cursor):
        print(f"result: {text_buffer_1.buffer_cursor}")
        print(f"expected: {text_buffer_2.menu_buffer_cursor}")


    text_buffer_1.update_buffer("nav_r")
    text_buffer_2.update_buffer("nav_r")
    print("Test 7")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print("Test 7")
        print(f"result: {output_1}")
        print(f"expected: {output_2}")
        print(f"result: {text_buffer_1.text_buffer}")
        print(f"expected: {text_buffer_2.text_buffer}")
    
    if(text_buffer_1.buffer_cursor != text_buffer_2.menu_buffer_cursor):
        print(f"result: {text_buffer_1.buffer_cursor}")
        print(f"expected: {text_buffer_2.menu_buffer_cursor}")

    for i in range(100):
        text_buffer_1.update_buffer("hello")
        text_buffer_2.update_buffer("hello")

    for _ in range(10): 
        text_buffer_1.update_buffer("nav_d")
        text_buffer_1.buffer()
        text_buffer_2.update_buffer("nav_d")
        text_buffer_2.buffer()

    print("Test 8")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print(f"result:\n{"\n".join(output_1)}")
        print(f"expected:\n{"\n".join(output_2)}")
        print(f"result:\n{text_buffer_1.text_buffer}")
        print(f"expected:\n{text_buffer_2.text_buffer}")

    
    if(text_buffer_1.buffer_cursor != text_buffer_2.menu_buffer_cursor):
        print(f"result: {text_buffer_1.buffer_cursor}")
        print(f"expected: {text_buffer_2.menu_buffer_cursor}")
    
    for i in range(10):
        text_buffer_1.update_buffer("nav_l")
        text_buffer_2.update_buffer("nav_l")

    print("Test 9")
    output_1 = text_buffer_1.buffer()
    output_2 = text_buffer_2.buffer()
    if(output_1 != output_2 or text_buffer_1.text_buffer != text_buffer_2.text_buffer):
        print(f"result:\n{"\n".join(output_1)}")
        print(f"expected:\n{"\n".join(output_2)}")
        print(f"result:\n{text_buffer_1.text_buffer}")
        print(f"expected:\n{text_buffer_2.text_buffer}")

    
    if(text_buffer_1.buffer_cursor != text_buffer_2.menu_buffer_cursor):
        print(f"result: {text_buffer_1.buffer_cursor}")
        print(f"expected: {text_buffer_2.menu_buffer_cursor}")

