import asyncio
import time

async def main():
    print("Hallo")
    task1 = asyncio.create_task(foo("hallo dude, ich warte 12 sek"))
    task2 = asyncio.create_task(foo2("ich warte 9 sek"))
    task3 = asyncio.create_task(get_input())
    asyncio.current_task
    print("alles getan")
    await task2
    print(task1.result())
    print(task3.result())
    
async def foo(text):
    print(text)
    
    await asyncio.sleep(12)
    print("heheh")
    return "hallo, du spacko"

async def get_input():
    inp = input("Gib was ein: ")
    print(inp)
    return inp


async def foo2(text):
    print(text)
    await asyncio.sleep(9)
    print("muahahha")
asyncio.run(main())

print("test")