import pandas as pd
from munch import Munch
from psycopg import connect, sql, OperationalError, Error
import random
import copy
from datetime import datetime, timedelta
from _classes.custom_dictionary import SpecialD
from kh_output.color_logs import color_logs


class PSQ:
    def __init__(self, database=None, user=None, password=None, host=None, port=5432, schema='public',
                 table_name=None, connection_name=None, logger=False, **kwargs):
        self.db_config = SpecialD(
            dbname=kwargs.get('dbname', database),
            user=kwargs.get('username', user),
            password=kwargs.get('password', password),
            host=kwargs.get('server', host),
            port=port
        )
        self.logger = logger or False
        self.name = connection_name or 'Database'

        self.schema = schema
        self.variables = Munch(**kwargs)
        self.connection = self.link()
        self.table_name = table_name if table_name else self.random_table()

    def link(self):
        try:
            a = connect(**self.db_config)
        except Exception as e:
            return print(f'error in connecting; {e}')
        return a

    def recon(self):
        if self.connection:
            self.connection.close()
        self.connection = self.link()
        if self.logger:
            self.logger.info('{name} made a connection: {schema}', {"name": self.name, "schema": self.schema})
        return self.connection

    def conn(self):
        return self.recon()

    def print_sets(self):
        a = self.db_config.copy()
        a['schema'] = self.schema
        a['variables'] = self.variables
        a['table_name'] = self.table_name
        return a

    def check_db(self, name=None):
        if name:
            db_name = name
        else:
            db_name = self.db_config[dbname]
        try:
            # Connect to the default database (e.g., postgres)
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking database existence: {e}")
            return False

    def table_exists(self, table_name=None, schema_name=None):
        if not table_name:
            raise ValueError("table_name must be provided.")

        # Use the schema from the class if not provided
        schema_name = schema_name or self.schema or 'public'

        query = sql.SQL("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_name = %s
            );
        """)

        try:
            with self.connection.cursor() as cursor:
                # Execute query with parameters as strings
                cursor.execute(query, (schema_name, table_name))
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error checking if table exists: {e}")
            return False

    def create_table(self, table_name, columns_defined, override_schema=None):
        """
        Create a new table dynamically.

        Parameters:
            schema_name (str): The schema name.
            table_name (str): The new table's name.
            columns (dict): Dictionary with column names as keys and data types as values.
        """
        # Start building the CREATE TABLE query
        if isinstance(override_schema, str):
            query = f'CREATE TABLE {override_schema}."{table_name}" ('
        else:
            query = f'CREATE TABLE {self.schema}."{table_name}" ('
        query += ', '.join([f'{col} {dtype}' for col, type in columns_defined.items()])
        query += ');'
        print(query)
        try:
            # Connect and execute the query
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                print(f"Table {schema_name}.{table_name} created successfully.")
        except Exception as e:
            print(f"Error creating table: {e}")

    def fetchall_tables(self):
        query = f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE';
                """

        with self.connection.cursor() as cursor:
            cursor.execute(query, (self.schema,))
            tables = cursor.fetchall()
        return [each[0] for each in tables]

    def fetchall_schema(self):
        query = """
                    SELECT table_schema, COUNT(*) AS table_count
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                    GROUP BY table_schema
                    ORDER BY table_schema;
                    """

        # Execute the query
        with self.connection.cursor() as cursor:
            # Execute the query
            cursor.execute(query)
            results = cursor.fetchall()

            # Close the cursor and connection
            # Convert results to a dictionary
            return {row[0]: row[1] for row in results}

    def swap_db(self, name=None, new_schema=None, new_table_name=None):
        # Create a deep copy of the current object
        new_instance = copy.deepcopy(self)

        # Modify the database name in the copy's configuration
        new_instance.db_config['dbname'] = name
        try:
            new_instance.recon()
        except Exception as e:
            print('error: ' + e)
            return self
        else:
            new_instance.name=name
            if new_schema:
                new_instance = new_instance.swap_schema(new_schema, new_table_name)
            # Reconnect the new instance
            new_instance.swap_table(new_table_name)

            return new_instance

    def swap_table(self, name=None):
        new_instance = copy.deepcopy(self)
        if isinstance(name, str) and self.table_exists(name):
            # Modify the database name in the copy's configuration
            new_instance.table_name = name
        else:
            new_instance.table_name = new_instance.random_table()
        new_instance.recon()
        return new_instance

    def swap_schema(self, name=None, table_name=None):
        new_instance = copy.deepcopy(self)
        new_instance.schema = name
        new_instance = new_instance.swap_table(table_name)
        return new_instance

    def random_table(self):
        """Fetch a random table name from the schema."""
        query = sql.SQL('''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY RANDOM()
            LIMIT 500
        ''')
        with self.conn().cursor() as cur:
            cur.execute(query, (self.schema,))
            tables = cur.fetchall()
            if not tables:
                raise ValueError(f"No tables found in schema '{self.schema}'.")
            return random.choice(tables)[0]

    def quick_random(self, limit=1, columns='*'):
        return self.quick_get(limit, columns, random=True)

    def quick_get(self, limit=1, columns='*', conditions=None, match_all=True, random=False, order_by=None,
                  ascending=True):
        # Prepare the WHERE clause
        where_clause = sql.SQL("")
        params = []  # Parameters for the query

        if conditions:
            if isinstance(conditions, list) and conditions:
                operator = ' AND ' if match_all else ' OR '
                where_clause = sql.SQL(" WHERE ") + sql.SQL(operator.join(["%s"] * len(conditions)))
                params.extend(conditions)
            elif isinstance(conditions, str):
                # For string conditions, use it as-is
                where_clause = sql.SQL(" WHERE ") + sql.SQL(conditions)

        # Handle ORDER BY clause
        order_clause = sql.SQL(" ORDER BY RANDOM()") if random else sql.SQL("")
        if order_by and not random:
            order_clause = sql.SQL(" ORDER BY {} {}").format(
                sql.Identifier(order_by),
                sql.SQL("ASC") if ascending else sql.SQL("DESC")
            )

        # Add LIMIT clause
        limit_clause = sql.SQL(" LIMIT %s")
        params.append(limit)

        # Build and execute the query
        with self.connection.cursor() as cur:
            query = (
                    sql.SQL(self._query_point_table(columns))
                    + where_clause
                    + order_clause
                    + limit_clause
            )
            cur.execute(query, params)

            # Handle single result (limit < 2)
            if limit < 2:
                r = cur.fetchone()
                if r is None:  # No rows returned
                    return None
                return r[0] if len(r) == 1 else r  # Return a single value if only one column

            # Handle multiple results (limit >= 2)
            r = cur.fetchall()
            if not r:  # No rows returned
                return []
            if len(r[0]) == 1:  # If single-column result, flatten the list
                return [row[0] for row in r]
            return r  # Multi-column result stays as list of tuples

    def cur_columns(self):
        if not self.schema or not self.table_name:
            raise ValueError("Schema and table name must be set.")
        query = sql.SQL("SELECT * FROM {}.{} LIMIT 1").format(
            sql.Identifier(self.schema),
            sql.Identifier(self.table_name)
        )
        try:
            with self.connection.cursor() as cur:
                cur.execute(query)
                result = [desc[0] for desc in cur.description]
                return result
        except Error as e:
            print(f"Error: Table '{self.schema}.{self.table_name}' does not exist. Details: {e}")
            return None

    def current_db(self):
        return self.db_config['dbname']

    def row_count(self, search_for='', limit=None, random=False, desc=False):
        """
        Gets row counts for tables in the schema. Falls back to COUNT(*) for tables with n_live_tup = 0.

        Parameters:
            search_for (str): Prefix to filter table names (default: '').

        Returns:
            dict: A dictionary with table names as keys and row counts as values.
        """
        # Query for general row counts using n_live_tup
        general_query = """
            SELECT relname AS table_name,
                   n_live_tup AS row_count
            FROM pg_stat_user_tables
            WHERE schemaname = %s
              AND relname ILIKE %s
        """
        if random:
            general_query += " ORDER BY RANDOM()"
        else:
            general_query += " ORDER BY relname"
        # Add LIMIT clause if provided
        if isinstance(limit, int) and limit > 0:
            general_query += f" LIMIT {limit}"
        search_pattern = search_for.replace('%', '\\%').replace('_', '\\_')

        # Add wildcards for partial matching, if necessary
        search_pattern = f'%{search_pattern}%'
        # Prepare the result dictionary
        table_counts = {}

        with self.connection.cursor() as cursor:
            # Execute the general query
            cursor.execute(general_query, (self.schema, search_pattern))
            results = cursor.fetchall()

        # Store the results in a dictionary
        for table_name, row_count in results:
            table_counts[table_name] = row_count

        # Fallback to COUNT(*) for tables with 0 rows
        for table_name, row_count in table_counts.items():
            if row_count == 0:
                specific_query = f'SELECT COUNT(*) FROM {self.schema}."{table_name}";'
                with self.connection.cursor() as cursor:
                    cursor.execute(specific_query)
                    exact_count = cursor.fetchone()[0]
                    table_counts[table_name] = exact_count

            # Sort the table counts by table name
        table_counts = SpecialD(table_counts).ordered_one(reverse=desc)

        return table_counts

    def analysis(self, filter_recent_days=30, max_retries=3):
        tables_to_analyze = self._late_analysis(filter_recent_days)
        if not tables_to_analyze:
            print(f"No tables in schema '{self.schema}' need ANALYZE.")
            return

        # Run ANALYZE on each table that needs it
        for (table_name,) in tables_to_analyze:
            retries = 0
            if self.table_exists(table_name, self.schema):
                while retries < max_retries:
                    try:
                        print(f"Running ANALYZE on {table_name}...")
                        self.connection.cursor().execute(sql.SQL("ANALYZE {}.{}").format(
                            sql.Identifier(self.schema),
                            sql.Identifier(table_name)
                        ))
                        break  # Exit retry loop on success
                    except OperationalError as e:
                        retries += 1
                        print(f"Retrying ANALYZE on {table_name} (Attempt {retries}/{max_retries})... Error: {e}")
                        time.sleep(2)  # Delay before retry
                else:
                    print(f"Failed to ANALYZE {table_name} after {max_retries} attempts.")
        print("ANALYZE complete for all necessary tables.")

    def alter_column(self, column_name, new_column_name=None, new_data_type=None):
        with self.connection.cursor() as cursor:
            if new_column_name:
                # Safely rename column
                rename_query = sql.SQL('ALTER TABLE {}.{} RENAME COLUMN {} TO {}').format(
                    sql.Identifier(self.schema),
                    sql.Identifier(self.table_name),
                    sql.Identifier(column_name),
                    sql.Identifier(new_column_name)
                )
                cursor.execute(rename_query)

            if new_data_type:
                # Safely change data type
                alter_query = sql.SQL('ALTER TABLE {}.{} ALTER COLUMN {} TYPE {}').format(
                    sql.Identifier(self.schema),
                    sql.Identifier(self.table_name),
                    sql.Identifier(new_column_name or column_name),
                    sql.SQL(new_data_type)  # Directly embed the new data type
                )
                cursor.execute(alter_query)

            self.connection.commit()

    def add_column(self, name, type="TEXT"):
        with self.connection.cursor() as cur:
            query = sql.SQL('ALTER TABLE {}.{} ADD COLUMN {} {}').format(
                sql.Identifier(self.schema),
                sql.Identifier(self.table_name),
                sql.Identifier(name),
                sql.SQL(type)  # Use sql.SQL for the data type
            )
            cur.execute(query)
            self.connection.commit()

    def column_my_list(self, list):
        return ', '.join(list)

    def write_row(self, data):
        """
        Inserts a row into the specified table using the provided dictionary.

        :param connection: A psycopg3 connection object
        :param table_name: The name of the table
        :param data: A dictionary where keys are column names and values are the data to insert
        """
        # Extract column names and values from the dictionary
        columns = data.keys()
        values = data.values()

        # Build the SQL query dynamically
        query = sql.SQL("""
            INSERT INTO {}.{} ({}) VALUES ({})
        """).format(
            sql.Identifier(self.schema),
            sql.Identifier(self.table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() for _ in values)
        )

        # Execute the query
        with self.connection.cursor() as cur:
            cur.execute(query, tuple(values))
            self.connection.commit()

    def write_rows(self, df):
        """
        Inserts multiple rows into the specified table using a pandas DataFrame.

        :param df: A pandas DataFrame where column names match the table's columns.
        """
        if df.empty:
            df = pd.DataFrame(df)

        # Extract column names and rows of values from the DataFrame
        columns = df.columns
        rows = df.values.tolist()

        # Build the SQL query dynamically
        query = sql.SQL("""
            INSERT INTO {}.{} ({}) VALUES ({})
        """).format(
            sql.Identifier(self.schema),
            sql.Identifier(self.table_name),
            sql.SQL(', ').join(map(sql.Identifier, columns)),
            sql.SQL(', ').join(sql.Placeholder() for _ in columns)
        )

        # Execute the query for all rows
        with self.connection.cursor() as cur:
            cur.executemany(query, rows)  # Use executemany for bulk insert
            self.connection.commit()

    def delete_rows(self, conditions):
        """
        Deletes rows from the specified table based on the provided conditions.

        :param connection: A psycopg3 connection object.
        :param schema: The schema of the table.
        :param table: The table name.
        :param conditions: A dictionary where keys are column names and values are the values to match for deletion.
        """
        # Build the WHERE clause dynamically
        where_clause = sql.SQL(" AND ").join(
            sql.SQL("{} = %s").format(sql.Identifier(column)) for column in conditions.keys()
        )

        query = sql.SQL("""
            DELETE FROM {}.{}
            WHERE {}
        """).format(
            sql.Identifier(self.schema),
            sql.Identifier(self.table_name),
            where_clause
        )

        # Execute the query
        with self.connection.cursor() as cur:
            cur.execute(query, tuple(conditions.values()))
            deleted_rows = cur.rowcoun
            self.connection.commit()
            print(f"{deleted_rows} rows deleted from {schema}.{table} where {conditions}.")

    def custon_execution(self, string, **params):
        query = sql.SQL(string).format(
            **{key: sql.Identifier(value) if key.endswith("_id") else sql.Placeholder(key) for key, value in
               params.items()}
        )

        with self.connection.cursor() as cur:
            # Extract only values for the placeholders
            placeholders = {key: value for key, value in params.items() if not key.endswith("_id")}

            cur.execute(query, placeholders)
            if query.get_type() == "SELECT":
                return cur.fetchall()
            self.connection.commit()

    def enable_logger(self, name, extra_colors=None, brute=False):
        self.logger = color_logs(name, extra_colors, clear_bully=brute)
        return self

    def _query_point_table(self, columns='*'):
        return f'SELECT {columns} FROM "{self.schema}"."{self.table_name}"'

    def _late_analysis(self, n_days_is_late=30):
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=n_days_is_late)
        try:
            with self.recon().cursor() as cursor:
                # Fetch table names in the schema
                query = """
                            SELECT relname
                            FROM pg_stat_user_tables
                            WHERE schemaname = %s
                              AND (last_analyze IS NULL OR last_analyze < %s);"""

                # Query to get tables that need ANALYZE
                cursor.execute(query, (self.schema, one_day_ago))
                return cursor.fetchall()

        except Exception as e:
            print(f"Error analyzing schema: {e}")

    def __deepcopy__(self, memo):
        # Create a shallow copy of the instance
        new_instance = self.__class__(**self.db_config, schema=self.schema, table_name=self.table_name)

        # Copy other attributes manually
        for attr, value in self.__dict__.items():
            if attr != 'connection':  # Exclude connection
                setattr(new_instance, attr, copy.deepcopy(value, memo))

        # Leave the connection uninitialized in the new instance
        new_instance.connection = None
        return new_instance

    def __del__(self):
        if self.connection and not self.connection.closed:
            self.connection.close()
            if self.logger:
                self.logger.info("{name} connection closed.", {"name": self.name})
