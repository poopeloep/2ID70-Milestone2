from pyspark import SparkConf, SparkContext, RDD
from pyspark.sql import SparkSession
from pyspark.streaming import StreamingContext
from pyspark.sql.functions import col
from pyspark.sql.functions import min as pspmin


def get_spark_context(on_server) -> SparkContext:
    spark_conf = SparkConf().setAppName("2ID70-MS2")
    if not on_server:
        spark_conf = spark_conf.setMaster("local[2]")
    return SparkContext.getOrCreate(spark_conf)

def wc_flatmap(r):
    print("r", r)
    l = []
    words = r.split(",")
    for word in words:
        l.append(word)
    return l

def wc_mappingrdd(l):
    m = []
    for rec in range(0, len(l)):
        if l[rec] == "R":
            records = l[rec].split(";") 
            numbers = l[rec].split(";")
            for (char, num) in zip(records, numbers):
                m.append(l[rec] + "," + char + "," + num)
        if l[rec] == "S":
            records = l[rec].split(";") 
            numbers = l[rec].split(";")
            for (char, num) in zip(records, numbers):
                m.append(l[rec] + "," + char + "," + num)
        if l[rec] == "T":
            records = l[rec].split(";") 
            numbers = l[rec].split(";")
            for (char, num) in zip(records, numbers):
                m.append(l[rec] + "," + char + "," + num)
    return m

def parse(row):
    records = []
    elements = row.split(',')

    relation_name = elements[0]
    attribute_names = elements[1].split(";")
    attribute_values = elements[2].split(";")

    relation = zip(attribute_names, attribute_values)

    for rel in list(relation):
        record = f"{relation_name}, {rel[0]}, {rel[1]}"
        records.append(record)

    return records

def q1(sc: SparkContext, on_server) -> RDD:
    database_file_path = "/Database.csv" if on_server else "2ID70-2022-MS2-Data-Small\Database.csv"

    # TODO: You may change the value for the minPartitions parameter (template value 160) when running locally.
    # It is advised (but not compulsory) to set the value to 160 when running on the server.
    database_rdd = sc.textFile(database_file_path, 160)
    
    record_groups = database_rdd.map(lambda r: parse(r) if not "AttributeValue" in r else "")
    record_lines = record_groups.flatMap(lambda r: r)
    
    # TODO: Implement Q1 here by defining q1RDD based on databaseRDD.
    q1_rdd = record_lines
    print(">> [q1: R: " + str(q1_rdd.filter(lambda r : r.split(",")[0].__eq__("R")).count()) + "]")
    print(">> [q1: S: " + str(q1_rdd.filter(lambda r : r.split(",")[0].__eq__("S")).count()) + "]")
    print(">> [q1: T: " + str(q1_rdd.filter(lambda r : r.split(",")[0].__eq__("T")).count()) + "]")

    return q1_rdd


def q2(spark_context: SparkContext, q1_rdd: RDD):
    spark_session = SparkSession(spark_context)
    #Create dataframe from RDD
    df = spark_session.createDataFrame(q1_rdd.map(lambda r: r.split(",")), schema = ["relation", "attribute", "value"])
    
    #Q2_1
    q21 = df.where("relation =='R'") \
            .count()
                
    #Q2_2
    distinct_values = df.groupBy("relation", "attribute", "value").count()
    q22 = distinct_values.groupBy("relation", "attribute") \
                .count().alias("count") \
                .where(col("count") >= 1000)
    
    #Q2_3
    q23 = distinct_values.groupBy('relation', 'attribute') \
                         .count().alias("count") \
                         .orderBy("count", ascending=True)
    q23 = q23.head(1)[0]

                 

    #Print results
    print(">> [q21: " + str(q21) + "]")
    print(">> [q22: " + str(q22.count()) + "]")
    print(">> [q23: " + f"{q23.__getitem__('relation')}.{q23.__getitem__('attribute')[1]}" + "]")

def q3(spark_context: SparkContext, q1_rdd: RDD):
    spark_session = SparkSession(spark_context)

    # TODO: Implement Q3 here
    split = q1_rdd.map(lambda r: r.split(", ")).map(lambda r: ((r[0],r[1]),r[2])).groupByKey().mapValues(list)
    relations = split.collect()
    relationCount = len(relations)

    for i in range(0, relationCount):
        rel1 = relations[i][1]
        for j in range(0, relationCount):
            if i != j:
                rel2 = relations[j][1]
                if len(list(set(rel1) & set(rel2))) == len(list(set(rel1))):
                    print(">> [q3: " + relations[i][0][0] + "." + relations[i][0][1] + "," + relations[j][0][0] + "." + relations[j][0][1] + "]")


def q4(spark_context: SparkContext, on_server):

    streaming_context = StreamingContext(spark_context, 2)
    streaming_context.checkpoint("checkpoint")

    hostname = "stream-host" if on_server else "localhost"
    lines = streaming_context.socketTextStream(hostname, 9000)

    # TODO: Implement Q4 here.
    #Get the total number of arrivals in the sliding window
    total_count = lines.countByWindow(20, 4)
    #Get the absolute frequencies of each ip in the sliding window
    absolute_freqs = lines.map(lambda line: (line, 1)).reduceByKeyAndWindow(lambda a, b: a+b, lambda a, b: a-b, 20, 4)
    #Combine both streams into one
    joined = absolute_freqs.transformWith(lambda freq, total: freq.cartesian(total), total_count)
    #Calculate the relative frequencies of each ip in the sliding window
    relative_freqs = joined.map(lambda freq: (freq[0][0], freq[0][1]/freq[1])).filter(lambda freq: freq[1] > 0.03)
    #Transform each pair into a correct output string
    freq_strings = relative_freqs.map(lambda freq: ">> [q4: " + freq[0] + "," + str(freq[1]) + "]")
    #Print the strings; there can't be more than 34 ip's with frequency > 3%, because 34*3% > 100%
    freq_strings.pprint(num=34)

    # Start the streaming context, run it for two minutes or until termination
    streaming_context.start()
    streaming_context.awaitTerminationOrTimeout(2 * 60)
    streaming_context.stop()


# Main 'function' which initializes a Spark context and runs the code for each question.
# To skip executing a question while developing a solution, simply comment out the corresponding function call.
if __name__ == '__main__':

    on_server = True  # TODO: Set this to true if and only if running on the server

    spark_context = get_spark_context(on_server)

    spark_context.setLogLevel("OFF")

    q1_rdd = q1(spark_context, on_server)

    q2(spark_context, q1_rdd)

    q3(spark_context, q1_rdd)

    q4(spark_context, on_server)

    spark_context.stop()
