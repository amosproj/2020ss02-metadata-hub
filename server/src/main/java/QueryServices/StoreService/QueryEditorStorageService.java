package QueryServices.StoreService;

import Database.Database;
import Database.DatabaseException;
import com.google.inject.Inject;

import java.io.IOException;
import java.sql.*;
import java.util.*;

public class QueryEditorStorageService
{

    private final Database database;

    @Inject
    public QueryEditorStorageService(Database database)
    {
        this.database = database;
    }

    public List<Map<String, String>> getAllStoredQueriesMetadata() throws DatabaseException, SQLException, IOException
    {
        try (Connection connection = database.getJDBCConnection())
        {
            PreparedStatement statement = connection.prepareStatement("SELECT author, create_time FROM stored_editor_queries");
            ResultSet resultSet = statement.executeQuery();

            ArrayList<StoredQueryMetadata> storedQueriesMetadata = new ArrayList<>();
            while(resultSet.next())
            {
                String author = resultSet.getString("author");
                Timestamp create_time = resultSet.getTimestamp("create_time");
                storedQueriesMetadata.add(new StoredQueryMetadata(author, create_time));
            }
        }

        return getAllStoredQueriesMetadata();
    }

    public StoredQuery getStoredQuery(long id) throws SQLException, IOException, DatabaseException
    {
        try (Connection connection = database.getJDBCConnection())
        {
            PreparedStatement statement = connection.prepareStatement("SELECT * FROM stored_editor_queries WHERE id=?");
            statement.setLong(1, id);
            ResultSet resultSet = statement.executeQuery();

            if (!resultSet.next()) return null;

            String author = resultSet.getString("author");
            Timestamp create_time = resultSet.getTimestamp("create_time");
            String data = resultSet.getString("data");

            StoredQueryMetadata storedQueryMetadata = new StoredQueryMetadata(author, create_time);
            return new StoredQuery(storedQueryMetadata, data);

        }
    }

    public void storeQuery(String author, String data) throws DatabaseException, SQLException, IOException
    {
        try (Connection connection = database.getJDBCConnection())
        {
            PreparedStatement statement = connection.prepareStatement("INSERT INTO stored_editor_queries VALUES (?, ?, ?::jsonb)");

            statement.setString(1, author);
            statement.setTimestamp(2, new Timestamp(System.currentTimeMillis()));
            statement.setString(3, data);
            statement.executeUpdate();
        }
    }

    public void deleteQuery(long id) throws DatabaseException, SQLException, IOException
    {
        try (Connection connection = database.getJDBCConnection())
        {
            PreparedStatement statement = connection.prepareStatement("DELETE FROM stored_editor_queries WHERE id = ?");
            statement.setLong(1, id);
            statement.executeUpdate();
        }
    }

    public void deleteAllQuery() throws DatabaseException, SQLException, IOException
    {
        try (Connection connection = database.getJDBCConnection())
        {
            PreparedStatement statement = connection.prepareStatement("DELETE FROM stored_editor_queries WHERE true");
            statement.executeUpdate();
        }
    }


}