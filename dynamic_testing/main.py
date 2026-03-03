# main.py
from graph.pipeline import build_graph


if __name__ == "__main__":
    graph = build_graph()

    user_query = """Server closed the connection: [WinError 10054] An existing connection was forcibly closed by the remote host
                    Connection error 1 during auth_key gen: ConnectionResetError: [WinError 10054] An existing connection was 
                    forcibly closed by the remote host
                    """

    result = graph.invoke({"query": user_query})
    print("\nFINAL RESULT:\n")
    # print(result["final_output"])
