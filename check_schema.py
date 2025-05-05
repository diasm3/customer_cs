import graphDB.neo4j

def check_neo4j_schema():
    """Neo4j 스키마를 확인하고 출력하는 함수"""
    print("Neo4j 스키마 확인 중...")
    
    try:
        schema = graphDB.neo4j.check_schema()
        print("Neo4j 스키마:")
        print(schema)
        return schema
    except Exception as e:
        print(f"Neo4j 스키마 확인 중 오류 발생: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    check_neo4j_schema()