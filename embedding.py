import asyncio
import openai
from graphDB.neo4j import Neo4jHybridSearch

# OpenAI API 키 설정

async def embed_neo4j_data_openai():
    """OpenAI 임베딩으로 Neo4j 데이터에 임베딩 추가"""
    
    print("OpenAI 임베딩 시작")
    
    # Neo4j 연결
    neo4j = Neo4jHybridSearch(
        uri="bolt://localhost:7687",
        username="neo4j", 
        password="password123"
    )
    
    try:
        # 임베딩이 없는 노드들 가져오기
        fetch_query = """
        MATCH (n:KnowledgeBase)
        WHERE n.embedding IS NULL OR size(n.embedding) = 0
        RETURN n.id as id, n.title as title, n.content as content
        LIMIT 50
        """
        
        def fetch_nodes():
            with neo4j.graph.session() as session:
                result = session.run(fetch_query)
                return list(result)
        
        nodes = await asyncio.to_thread(fetch_nodes)
        print(f"임베딩할 노드: {len(nodes)}개")
        
        # 업데이트 쿼리
        update_query = """
        MATCH (n:KnowledgeBase {id: $id})
        SET n.embedding = $embedding
        RETURN n.id
        """
        
        for i, node in enumerate(nodes):
            try:
                # 텍스트 결합
                text = f"{node['title']} {node['content']}"
                
                # OpenAI 임베딩 생성
                response = await asyncio.to_thread(
                    lambda: openai.embeddings.create(
                        input=text,
                        model="text-embedding-3-small"
                    )
                )
                
                embedding = response.data[0].embedding
                
                # Neo4j 업데이트
                def update_node():
                    with neo4j.graph.session() as session:
                        session.run(update_query, {
                            "id": node["id"],
                            "embedding": embedding
                        })
                
                await asyncio.to_thread(update_node)
                print(f"임베딩 완료: {i+1}/{len(nodes)} - {node['title']}")
                
            except Exception as e:
                print(f"임베딩 실패: {node['id']} - {e}")
        
        # 벡터 인덱스 생성 (OpenAI는 1536 차원)
        index_query = """
        CREATE VECTOR INDEX embedding_index IF NOT EXISTS
        FOR (n:KnowledgeBase) ON (n.embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 1536,
            `vector.similarity_function`: 'cosine'
        }}
        """
        
        def create_index():
            with neo4j.graph.session() as session:
                session.run(index_query)
        
        await asyncio.to_thread(create_index)
        print("벡터 인덱스 생성 완료")
        
    except Exception as e:
        print(f"임베딩 과정에서 오류: {e}")
    finally:
        await neo4j.async_close()

if __name__ == "__main__":
    asyncio.run(embed_neo4j_data_openai())