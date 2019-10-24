import java.io.File;
import java.io.IOException;

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
        String path = System.getProperty("user.dir") + "/Address.csv";
        System.out.println(path);
        String csvData = Files.readString(Paths.get(path));

        CSVFormat myFmt = CSVFormat.RFC4180.withRecordSeparator("\n\n");

        CSVParser parser = CSVParser.parse(csvData.toString(), myFmt);
        for (CSVRecord record : parser) {
            System.out.println(record);
        }
    }
}
