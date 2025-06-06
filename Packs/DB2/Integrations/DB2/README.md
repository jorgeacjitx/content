Integration to provide connectivity to IBM DB2 using the python ibm_db2 library.
This integration was integrated and tested with version 0.1 of DB2

## Configure DB2 in Cortex

| **Parameter** | **Required** |
| --- | --- |
| Database host | True |
| Port | False |
| Database Name | False |
| Username | True |
| Password | True |
| Connection Arguments (ex: arg1=val1&amp;arg2=val2) | False |
| Use an SSL connection | False |
| Use Persistent Connection | False |

## Commands

You can execute these commands from the CLI, as part of an automation, or in a playbook.
After you successfully execute a command, a DBot message appears in the War Room with the command details.

### db2-query

***
Running a DB2 query command

#### Base Command

`db2-query`

#### Input

| **Argument Name** | **Description** | **Required** |
| --- | --- | --- |
| query | The DB2 query to run. | Required |
| limit | The maximum number of results. Default is 50. | Optional |
| skip | The offset at which to start the result. Default is 0. | Optional |
| bind_variables_name | A comma separated list of names which will be replaced in query having ':&lt;name&gt;'. | Optional |
| bind_variables_values | A comma separated list of values corresponding to `bind_variables_name` or values in order of '?' mark to be replaced in query. | Optional |

#### Context Output

There is no context output for this command.

#### Command Example

```!db2-query query="CREATE TABLE publishers(publisher_id INT GENERATED BY DEFAULT AS IDENTITY NOT NULL, name VARCHAR(255) NOT NULL, PRIMARY KEY(publisher_id))"```

#### Human Readable Output
