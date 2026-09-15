import psycopg2
from typing import Dict, Any, Optional, List


class DatabaseUtil:
    """
    Database utility for PostgreSQL schema extraction and read-only query execution.
    Enforces transaction-level read-only mode and execution timeouts.
    """

    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config

    def get_connection(self):
        """Create a fresh database connection with a 10s connect timeout."""
        try:
            conn = psycopg2.connect(**self.db_config, connect_timeout=10)
            return conn
        except Exception as e:
            raise RuntimeError(f"Failed to connect to PostgreSQL database: {e}") from e

    def schema_details(self, schema_name: str = "public") -> str:
        """
        Fetch schema metadata (tables, columns, types, and sample data)
        for the given schema.
        """
        connection = None
        cursor = None
        schema_info_context = f"Database Schema: {schema_name}\n"

        try:
            connection = self.get_connection()
            cursor = connection.cursor()

            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name;",
                (schema_name,)
            )
            tables_list = cursor.fetchall()

            if not tables_list:
                return f"No tables found in schema '{schema_name}'."

            for table in tables_list:
                table_name = table[0]
                schema_info_context += f"\nTable: {table_name}\n"

                # Adding Columns & Data Types
                cursor.execute(
                    "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position;",
                    (table_name,)
                )
                columns_list = cursor.fetchall()

                for column in columns_list:
                    column_name = column[0]
                    data_type = column[1]
                    schema_info_context += f"  Column: {column_name}, Data Type: {data_type}\n"

                # Adding Sample Data (read-only preview)
                try:
                    cursor.execute(f"SELECT * FROM {schema_name}.{table_name} LIMIT 5;")
                    sample_data = cursor.fetchall()
                    schema_info_context += "  Sample Data:\n"
                    for row in sample_data:
                        schema_info_context += f"    {row}\n"
                except Exception as sample_err:
                    schema_info_context += f"  Sample Data unavailable: {sample_err}\n"

            return schema_info_context

        except Exception as e:
            error_msg = f"Error fetching schema details: {e}"
            print(error_msg)
            return error_msg

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def execute_sql(self, query: str) -> str:
        """
        Execute an already-validated SQL query using
        transaction-level read-only mode and timeouts.
        """
        connection = None
        cursor = None

        try:
            connection = self.get_connection()
            with connection.cursor() as cursor:
                # Enforce transaction-level safety limits
                cursor.execute("SET TRANSACTION READ ONLY;")
                cursor.execute("SET LOCAL statement_timeout = '10s';")
                cursor.execute("SET LOCAL idle_in_transaction_session_timeout = '15s';")

                cursor.execute(query)

                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchmany(1000)
                    
                    if not rows:
                        return "Query executed successfully. Result: 0 rows returned."
                    
                    # Format into a clean string representation for the LLM
                    header = " | ".join(columns)
                    separator = "-" * len(header)
                    row_strs = [" | ".join(str(val) for val in row) for row in rows]
                    table_str = f"Columns: {columns}\nRows ({len(rows)} returned):\n" + "\n".join(row_strs)
                    return table_str
                else:
                    return "Query executed successfully with no returned rows."

        except Exception as e:
            error_msg = f"Database query execution failed: {e}"
            print(error_msg)
            return f"Error: {error_msg}"

        finally:
            if connection:
                connection.close()

    def execute_select(self, query: str) -> str:
        """Alias for execute_sql for backwards compatibility."""
        return self.execute_sql(query)


if __name__ == "__main__":
    db_config = {
        "host": "localhost",
        "port": 5432,
        "user": "sql_agent_reader",
        "password": "26102005harshil",
        "dbname": "postgres"
    }

    try:
        obj = DatabaseUtil(db_config)
        result = obj.schema_details("public")
        with open("test_schema_details.txt", "w", encoding="utf-8") as f:
            f.write(result)
        print("Schema details successfully written to test_schema_details.txt")
    except Exception as err:
        print(f"Database connection test skipped/failed: {err}")