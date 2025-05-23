# utils/keyword_analyzer.py
import re
import asyncio
from collections import Counter
from typing import List, Dict, Set

# 토크나이저 및 불용어 처리 라이브러리
from konlpy.tag import Okt, Mecab
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import spacy

# 임베딩 라이브러리
from sentence_transformers import SentenceTransformer

# NLTK 데이터 다운로드 (최초 실행시)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# spaCy 모델 로드 (영어)
try:
    nlp_en = spacy.load("en_core_web_sm")
except OSError:
    print("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
    nlp_en = None

# 한국어 형태소 분석기 초기화
try:
    korean_tokenizer = Okt()
except Exception:
    try:
        korean_tokenizer = Mecab()
    except Exception:
        korean_tokenizer = None
        print("Korean tokenizer not available. Install KoNLPy: pip install konlpy")

# NLTK 불용어 로드
try:
    ENGLISH_STOPWORDS = set(stopwords.words('english'))
    KOREAN_STOPWORDS = set(stopwords.words('korean')) if 'korean' in stopwords.fileids() else set()
except:
    ENGLISH_STOPWORDS = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it',
        'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with', 'the', 'this', 'but', 'they',
        'have', 'had', 'what', 'said', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 'up', 'out',
        'many', 'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'into', 'him',
        'time', 'two', 'more', 'very', 'when', 'come', 'may', 'its', 'only', 'think', 'now', 'work',
        'life', 'also', 'way', 'after', 'back', 'other', 'well', 'get', 'through', 'new', 'year', 'could'
    }
    KOREAN_STOPWORDS = {
        '이', '그', '저', '것', '의', '가', '을', '를', '에', '와', '과', '도', '는', '은', '으로', '로', 
        '에서', '부터', '까지', '이다', '있다', '없다', '하다', '되다', '같다', '다른', '많다', '적다',
        '좋다', '나쁘다', '크다', '작다', '높다', '낮다', '그리고', '또는', '하지만', '그러나', '그래서',
        '따라서', '즉', '또한', '예를 들어', '때문에', '위해', '아니다', '수', '개', '명', '번', '등',
        '및', '또', '더', '가장', '매우', '정말', '아주', '너무', '조금', '약간', '거의', '완전히',
        '전혀', '항상', '때로는', '가끔', '자주', '드물게', '언제나', '결코', '절대', '모든', '어떤',
        '각각', '서로', '함께', '혼자', '다시', '새로', '이미', '아직', '계속', '다음', '이전', '현재',
        '과거', '미래', '여기', '거기', '어디', '언제', '어떻게', '왜', '무엇', '누구', '얼마나'
    }

# 임베딩 모델 초기화 (전역)
embedding_model = None

def get_embedding_model():
    """임베딩 모델 싱글톤"""
    global embedding_model
    if embedding_model is None:
        try:
            embedding_model = SentenceTransformer('distiluse-base-multilingual-cased')
        except Exception as e:
            print(f"Embedding model load failed: {e}")
            embedding_model = None
    return embedding_model

# 임베딩 라이브러리
import openai

# OpenAI 클라이언트 초기화
openai_client = None

def get_openai_client():
    """OpenAI 클라이언트 싱글톤"""
    global openai_client
    if openai_client is None:
        try:
            openai_client = openai.OpenAI()  # API 키는 환경변수에서 자동 로드
        except Exception as e:
            print(f"OpenAI client initialization failed: {e}")
            openai_client = None
    return openai_client

class AdvancedTokenizer:
    """고급 토크나이저 - 라이브러리 기반 형태소 분석 및 핵심 단어 추출"""
    
    def __init__(self):
        self.korean_tokenizer = korean_tokenizer
        self.english_stopwords = ENGLISH_STOPWORDS
        self.korean_stopwords = KOREAN_STOPWORDS
        self.nlp_en = nlp_en
        
    def korean_morphological_analysis(self, text: str) -> List[str]:
        """한국어 형태소 분석하여 핵심 단어만 추출"""
        if not self.korean_tokenizer:
            return text.split()
            
        try:
            pos_tags = self.korean_tokenizer.pos(text, stem=True)
            meaningful_pos = ['Noun', 'Verb', 'Adjective', 'Adverb', 'Alpha', 'Number']
            
            keywords = []
            for word, pos in pos_tags:
                if (pos in meaningful_pos and 
                    len(word) >= 2 and 
                    word not in self.korean_stopwords):
                    keywords.append(word)
            
            return keywords
        except Exception as e:
            print(f"Korean tokenization error: {e}")
            return text.split()
    
    def english_morphological_analysis(self, text: str) -> List[str]:
        """영어 형태소 분석하여 핵심 단어만 추출"""
        try:
            if self.nlp_en:
                doc = self.nlp_en(text)
                keywords = []
                for token in doc:
                    if (not token.is_stop and 
                        not token.is_punct and 
                        not token.is_space and
                        token.pos_ in ['NOUN', 'VERB', 'ADJ', 'ADV'] and
                        len(token.lemma_) >= 2):
                        keywords.append(token.lemma_.lower())
                return keywords
            else:
                tokens = word_tokenize(text.lower())
                return [word for word in tokens 
                       if word not in self.english_stopwords 
                       and len(word) >= 2 
                       and word.isalpha()]
        except Exception as e:
            print(f"English tokenization error: {e}")
            return text.split()
    
    def extract_core_keywords(self, text: str) -> List[str]:
        """텍스트에서 핵심 키워드만 추출"""
        korean_text = re.findall(r'[가-힣]+', text)
        english_text = re.findall(r'[a-zA-Z]+', text)
        
        keywords = []
        
        if korean_text:
            korean_sentence = ' '.join(korean_text)
            korean_keywords = self.korean_morphological_analysis(korean_sentence)
            keywords.extend(korean_keywords)
        
        if english_text:
            english_sentence = ' '.join(english_text)
            english_keywords = self.english_morphological_analysis(english_sentence)
            keywords.extend(english_keywords)
        
        numbers = re.findall(r'\d+', text)
        keywords.extend(numbers)
        
        return list(set(keywords))

class KeywordAnalyzer:
    """사용자 질문에서 키워드를 추출하고 분석하는 클래스"""
    
    def __init__(self):
        self.tokenizer = AdvancedTokenizer()
        
    def preprocess_text(self, text: str) -> str:
        """텍스트 전처리"""
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_keywords(self, text: str, min_length: int = 2, max_keywords: int = 10) -> List[Dict]:
        """라이브러리 기반 키워드 추출 및 빈도 분석"""
        processed_text = self.preprocess_text(text)
        core_keywords = self.tokenizer.extract_core_keywords(processed_text)
        filtered_keywords = [word for word in core_keywords if len(word) >= min_length]
        
        word_counts = Counter(filtered_keywords)
        top_keywords = word_counts.most_common(max_keywords)
        
        keywords_info = []
        total_words = len(filtered_keywords)
        for keyword, count in top_keywords:
            keywords_info.append({
                'keyword': keyword,
                'frequency': count,
                'importance': count / total_words if total_words > 0 else 0,
                'normalized_form': keyword
            })
        
        return keywords_info
    
    def transform_query_to_keywords(self, query: str) -> str:
        """쿼리를 핵심 키워드만으로 변환"""
        keywords_info = self.extract_keywords(query, min_length=1, max_keywords=20)
        core_keywords = [item['keyword'] for item in keywords_info]
        transformed_query = ' '.join(core_keywords)
        
        print(f"Original query: {query}")
        print(f"Transformed query: {transformed_query}")
        
        return transformed_query
    
    def categorize_keywords(self, keywords: List[Dict], categories: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
        """키워드를 카테고리별로 분류"""
        categorized = {category: [] for category in categories.keys()}
        categorized['기타'] = []
        
        for keyword_info in keywords:
            keyword = keyword_info['keyword']
            categorized_flag = False
            
            for category, category_words in categories.items():
                if keyword in category_words or any(cat_word in keyword for cat_word in category_words):
                    categorized[category].append(keyword_info)
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                categorized['기타'].append(keyword_info)
        
        return categorized

async def analyze_user_query_keywords(query: str, company_id: str = None) -> Dict:
    """사용자 질문의 키워드를 분석하고 의도를 파악"""
    analyzer = KeywordAnalyzer()
    
    keywords = analyzer.extract_keywords(query)
    transformed_query = analyzer.transform_query_to_keywords(query)
    
    business_categories = {
        '제품/서비스': ['제품', '서비스', '상품', '솔루션', '기능', '특징', '가격', '비용', '요금', 'product', 'service', 'price'],
        '고객지원': ['문의', '질문', '도움', '지원', '상담', '문제', '해결', '답변', '설명', 'help', 'support', 'question'],
        '주문/결제': ['주문', '구매', '결제', '카드', '계좌', '배송', '주소', '수량', '할인', 'order', 'payment', 'buy'],
        '기술/기능': ['사용법', '설정', '설치', '연결', '로그인', '계정', '비밀번호', '업데이트', 'install', 'setup', 'login'],
        '정책/약관': ['정책', '약관', '규정', '조건', '환불', '취소', '교환', '보증', '개인정보', 'policy', 'terms', 'refund']
    }
    
    categorized_keywords = analyzer.categorize_keywords(keywords, business_categories)
    
    intent_patterns = {
        '정보요청': ['무엇', '어떤', '어떻게', '언제', '어디서', '왜', '설명', '알려', 'what', 'how', 'when', 'where', 'why'],
        '문제해결': ['문제', '오류', '안됨', '작동', '해결', '고장', '버그', 'problem', 'error', 'fix', 'broken'],
        '구매의도': ['구매', '사고싶', '주문', '결제', '가격', '할인', '비용', 'buy', 'purchase', 'order', 'price'],
        '불만/개선': ['불만', '개선', '문제', '이상', '잘못', '실망', 'complaint', 'improve', 'wrong', 'disappointed']
    }
    
    detected_intent = '일반문의'
    for intent, patterns in intent_patterns.items():
        if any(pattern in transformed_query for pattern in patterns):
            detected_intent = intent
            break
    
    return {
        'raw_query': query,
        'transformed_query': transformed_query,
        'total_keywords': len(keywords),
        'top_keywords': keywords[:5],
        'categorized_keywords': categorized_keywords,
        'detected_intent': detected_intent,
        'query_length': len(query),
        'complexity_score': len(keywords) * 0.1 + len(query.split()) * 0.05
    }

async def preprocess_and_search_neo4j(original_query: str, transformed_query: str, neo4j_search) -> List[Dict]:
    """키워드 기반 Neo4j 풀텍스트 검색"""
    try:
        # 키워드 추출
        analyzer = KeywordAnalyzer()
        keywords_info = analyzer.extract_keywords(transformed_query, min_length=2, max_keywords=10)
        
        excluded_words = {'어떻다', '되다', '있다', '하다', '이다', '같다', '보다', '말하다'}
        keywords = [k['keyword'] for k in keywords_info 
                   if k['keyword'] not in excluded_words and len(k['keyword']) >= 2]
        
        # 원본 쿼리에서 직접 키워드 추출 + 동의어 매핑
        if len(keywords) < 2:
            direct_keywords = []
            # 심카드/유심 동의어 처리
            if '심카드' in original_query or '유심' in original_query:
                direct_keywords.extend(['유심', '심카드'])
            if '유출' in original_query:
                direct_keywords.append('유출')
            if '사건' in original_query or '사태' in original_query:
                direct_keywords.extend(['사건', '사태'])
            if '해킹' in original_query:
                direct_keywords.extend(['해킹', '침입'])
            keywords.extend(direct_keywords)
        
        # 동의어 확장
        synonym_map = {
            '심카드': ['유심', '심카드', 'USIM', 'SIM'],
            '유심': ['유심', '심카드', 'USIM', 'SIM'],
            '사건': ['사건', '사태', '문제'],
            '해킹': ['해킹', '침입', '탈취']
        }
        
        expanded_keywords = []
        for keyword in keywords:
            if keyword in synonym_map:
                expanded_keywords.extend(synonym_map[keyword])
            else:
                expanded_keywords.append(keyword)
        
        keywords = list(set(expanded_keywords))  # 중복 제거
        
        if not keywords:
            return await neo4j_search.async_hybrid_search(original_query, {})
        
        # 검색 쿼리 생성 - 공백으로 분리 (Neo4j 풀텍스트는 기본적으로 OR 처리)
        search_query = " ".join(keywords[:3])  # 상위 3개 키워드만
        print(f"Neo4j fulltext search query: {search_query}")
        
        # 풀텍스트 검색 쿼리
        cypher = """
        CALL db.index.fulltext.queryNodes('knowledge_search', $query)
        YIELD node, score 
        WHERE score > 0.3
        RETURN node.content as content, 
               node.title as title, 
               score 
        ORDER BY score DESC 
        LIMIT 3
        """
        
        def execute_search():
            with neo4j_search.graph.session() as session:
                result = session.run(cypher, {"query": search_query})
                return list(result)
        
        records = await asyncio.to_thread(execute_search)
        
        search_results = []
        for record in records:
            content = record.get('content', '')
            if content and content.strip():
                search_results.append({
                    'content': content,
                    'title': record.get('title', ''),
                    'score': record.get('score', 0.0)
                })
        
        print(f"Found {len(search_results)} fulltext results")
        return search_results if search_results else await neo4j_search.async_hybrid_search(original_query, {})
        
    except Exception as e:
        print(f"Neo4j fulltext search error: {e}")
        return await neo4j_search.async_hybrid_search(original_query, {})

async def vector_search_neo4j(query: str, neo4j_search, limit: int = 3) -> List[Dict]:
    """OpenAI 임베딩을 사용한 벡터 유사도 검색"""
    try:
        client = get_openai_client()
        if not client:
            return []
        
        # OpenAI 임베딩 생성
        def create_embedding():
            response = client.embeddings.create(
                input=query,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
        
        query_embedding = await asyncio.to_thread(create_embedding)
        
        # 벡터 검색 쿼리 (디버깅용 - 임계값 제거)
        vector_cypher = """
        CALL db.index.vector.queryNodes('embedding_index', $limit, $queryEmbedding)
        YIELD node, score
        RETURN node.content as content, 
               node.title as title, 
               score
        ORDER BY score DESC
        """
        
        def execute_vector_search():
            with neo4j_search.graph.session() as session:
                result = session.run(vector_cypher, {
                    "queryEmbedding": query_embedding,
                    "limit": limit
                })
                return list(result)
        
        records = await asyncio.to_thread(execute_vector_search)
        
        return [{
            'content': r.get('content', ''),
            'title': r.get('title', ''),
            'score': r.get('score', 0.0)
        } for r in records if r.get('content')]
        
    except Exception as e:
        print(f"Vector search error: {e}")
        return []

async def hybrid_search_neo4j(original_query: str, transformed_query: str, neo4j_search) -> List[Dict]:
    """하이브리드 검색: 풀텍스트 + 벡터 검색"""
    try:
        # 1. 풀텍스트 검색
        fulltext_results = await preprocess_and_search_neo4j(
            original_query, transformed_query, neo4j_search
        )
        
        # 2. 벡터 검색
        vector_results = await vector_search_neo4j(original_query, neo4j_search)
        
        # 3. 결과 합성 및 중복 제거
        combined_results = []
        seen_content = set()
        
        # 풀텍스트 결과 (가중치 1.0)
        for result in fulltext_results:
            content = result['content']
            if content not in seen_content:
                combined_results.append({
                    **result,
                    'search_type': 'fulltext',
                    'final_score': result['score']
                })
                seen_content.add(content)
        
        # 벡터 결과 (가중치 0.8)
        for result in vector_results:
            content = result['content']
            if content not in seen_content:
                combined_results.append({
                    **result,
                    'search_type': 'vector',
                    'final_score': result['score'] * 0.8
                })
                seen_content.add(content)
        
        # 점수순 정렬
        combined_results.sort(key=lambda x: x['final_score'], reverse=True)
        
        print(f"Hybrid search: {len(fulltext_results)} fulltext + {len(vector_results)} vector = {len(combined_results)} total")
        
        return combined_results[:5] if combined_results else await neo4j_search.async_hybrid_search(original_query, {})
        
    except Exception as e:
        print(f"Hybrid search error: {e}")
        return await neo4j_search.async_hybrid_search(original_query, {})