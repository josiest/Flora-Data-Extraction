import java.io.File;
import java.io.IOException;

import java.util.Map;
import java.util.HashMap;

import com.healthmarketscience.jackcess.Database;
import com.healthmarketscience.jackcess.DatabaseBuilder;
import com.healthmarketscience.jackcess.Table;
import com.healthmarketscience.jackcess.TableBuilder;
import com.healthmarketscience.jackcess.ColumnBuilder;
import com.healthmarketscience.jackcess.IndexBuilder;
import com.healthmarketscience.jackcess.DataType;
import com.healthmarketscience.jackcess.Row;

import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;
import org.apache.commons.csv.CSVFormat;

import java.nio.file.Files;
import java.nio.file.Paths;

public class Address {
    public static void main(String[] args) throws IOException {
        // fields of the table
        String[] fields = {"Address", "Acronym", "Name", "Institution",
                           "Position"};
        // path to the csv file with the addresses
        String path = System.getProperty("user.dir") + "/Address.csv";
        // get the data into a string
        String csvData = Files.readString(Paths.get(path));

        // record separators are two lines and header is specified by fields
        CSVFormat myFmt = CSVFormat.RFC4180
            .withRecordSeparator("\n\n")
            .withHeader(fields);

        // Create the database
        File file = new File("address.accdb");
        Database db = new DatabaseBuilder(file)
            .setFileFormat(Database.FileFormat.V2010)
            .create();

        // Build the table
        TableBuilder tb = new TableBuilder("Addresses");
        for (String field : fields) {
            tb = tb.addColumn(new ColumnBuilder(field, DataType.TEXT));
        }
        Table tab = tb.toTable(db);

        // import the csv data
        CSVParser parser = CSVParser.parse(csvData.toString(), myFmt);
        for (CSVRecord record : parser) {
            // this is a dumb hack. for some reason the csv import is including
            // null lines even though I thought I'd specified it not to by using
            // CSVFormat.RFC4180. This just skips the record if it's null
            if (record.size() <= 1) {
                continue;
            }
            // Create a map of fields to their values and add it to the table
            Map<String, Object> row = new HashMap<>();
            for (String field : fields) {
                row.put(field, record.get(field));
            }
            tab.addRowFromMap(row);
        }
        db.close();
    }
}
