import pynet

def main():
    server = pynet.Server()
    server.serve(("localhost", 987))

if __name__ == "__main__":
    main()
    input("Press enter to exit.")
