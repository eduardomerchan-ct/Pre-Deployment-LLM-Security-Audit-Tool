from targets.direct_api import DirectAPIAdapter

a = DirectAPIAdapter()
r1 = a.send("My name is Alex.") 
r2 = a.send("What's my name?", history=r1.raw)
print(r2.text)
