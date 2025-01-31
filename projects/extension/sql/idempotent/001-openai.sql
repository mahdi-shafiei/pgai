
-------------------------------------------------------------------------------
-- openai_tokenize
-- encode text as tokens for a given model
-- https://github.com/openai/tiktoken/blob/main/README.md
create or replace function ai.openai_tokenize(model text, text_input text) returns int[]
as $python$
    #ADD-PYTHON-LIB-DIR
    import tiktoken
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text_input)
    return tokens
$python$
language plpython3u strict immutable parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_detokenize
-- decode tokens for a given model back into text
-- https://github.com/openai/tiktoken/blob/main/README.md
create or replace function ai.openai_detokenize(model text, tokens int[]) returns text
as $python$
    #ADD-PYTHON-LIB-DIR
    import tiktoken
    encoding = tiktoken.encoding_for_model(model)
    content = encoding.decode(tokens)
    return content
$python$
language plpython3u strict immutable parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_list_models
-- list models supported on the openai platform
-- https://platform.openai.com/docs/api-reference/models/list
create or replace function ai.openai_list_models(api_key text default null, api_key_name text default null, base_url text default null)
returns table
( id text
, created timestamptz
, owned_by text
)
as $python$
    #ADD-PYTHON-LIB-DIR
    import ai.openai
    import ai.secrets
    api_key_resolved = ai.secrets.get_secret(plpy, api_key, api_key_name, ai.openai.DEFAULT_KEY_NAME, SD)
    for tup in ai.openai.list_models(plpy, api_key_resolved, base_url):
        yield tup
$python$
language plpython3u volatile parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_embed
-- generate an embedding from a text value
-- https://platform.openai.com/docs/api-reference/embeddings/create
create or replace function ai.openai_embed
( model text
, input_text text
, api_key text default null
, api_key_name text default null
, base_url text default null
, dimensions int default null
, openai_user text default null
) returns @extschema:vector@.vector
as $python$
    #ADD-PYTHON-LIB-DIR
    import ai.openai
    import ai.secrets
    api_key_resolved = ai.secrets.get_secret(plpy, api_key, api_key_name, ai.openai.DEFAULT_KEY_NAME, SD)
    for tup in ai.openai.embed(plpy, model, input_text, api_key=api_key_resolved, base_url=base_url, dimensions=dimensions, user=openai_user):
        return tup[1]
$python$
language plpython3u immutable parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_embed
-- generate embeddings from an array of text values
-- https://platform.openai.com/docs/api-reference/embeddings/create
create or replace function ai.openai_embed
( model text
, input_texts text[]
, api_key text default null
, api_key_name text default null
, base_url text default null
, dimensions int default null
, openai_user text default null
) returns table
( "index" int
, embedding @extschema:vector@.vector
)
as $python$
    #ADD-PYTHON-LIB-DIR
    import ai.openai
    import ai.secrets
    api_key_resolved = ai.secrets.get_secret(plpy, api_key, api_key_name, ai.openai.DEFAULT_KEY_NAME, SD)
    for tup in ai.openai.embed(plpy, model, input_texts, api_key=api_key_resolved, base_url=base_url, dimensions=dimensions, user=openai_user):
        yield tup
$python$
language plpython3u immutable parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_embed
-- generate embeddings from an array of tokens
-- https://platform.openai.com/docs/api-reference/embeddings/create
create or replace function ai.openai_embed
( model text
, input_tokens int[]
, api_key text default null
, api_key_name text default null
, base_url text default null
, dimensions int default null
, openai_user text default null
) returns @extschema:vector@.vector
as $python$
    #ADD-PYTHON-LIB-DIR
    import ai.openai
    import ai.secrets
    api_key_resolved = ai.secrets.get_secret(plpy, api_key, api_key_name, ai.openai.DEFAULT_KEY_NAME, SD)
    for tup in ai.openai.embed(plpy, model, input_tokens, api_key=api_key_resolved, base_url=base_url, dimensions=dimensions, user=openai_user):
        return tup[1]
$python$
language plpython3u immutable parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_chat_complete
-- text generation / chat completion
-- https://platform.openai.com/docs/api-reference/chat/create
create or replace function ai.openai_chat_complete
( model text
, messages jsonb
, api_key text default null
, api_key_name text default null
, base_url text default null
, frequency_penalty float8 default null
, logit_bias jsonb default null
, logprobs boolean default null
, top_logprobs int default null
, max_tokens int default null
, n int default null
, presence_penalty float8 default null
, response_format jsonb default null
, seed int default null
, stop text default null
, temperature float8 default null
, top_p float8 default null
, tools jsonb default null
, tool_choice text default null
, openai_user text default null
) returns jsonb
as $python$
    #ADD-PYTHON-LIB-DIR
    import ai.openai
    import ai.secrets
    api_key_resolved = ai.secrets.get_secret(plpy, api_key, api_key_name, ai.openai.DEFAULT_KEY_NAME, SD)
    client = ai.openai.make_client(plpy, api_key_resolved, base_url)
    import json

    messages_1 = json.loads(messages)
    if not isinstance(messages_1, list):
      plpy.error("messages is not an array")

    args = {}

    if frequency_penalty is not None:
      args["frequency_penalty"] = frequency_penalty

    if logit_bias is not None:
      args["logit_bias"] = json.loads(logit_bias)

    if logprobs is not None:
      args["logprobs"] = logprobs

    if top_logprobs is not None:
      args["top_logprobs"] = top_logprobs

    if max_tokens is not None:
      args["max_tokens"] = max_tokens

    if n is not None:
      args["n"] = n

    if presence_penalty is not None:
      args["presence_penalty"] = presence_penalty

    if response_format is not None:
      args["response_format"] = json.loads(response_format)

    if seed is not None:
        args["seed"] = seed

    if stop is not None:
      args["stop"] = stop

    if temperature is not None:
      args["temperature"] = temperature

    if top_p is not None:
      args["top_p"] = top_p

    if tools is not None:
      args["tools"] = json.loads(tools)

    if tool_choice is not None:
      args["tool_choice"] = tool_choice if tool_choice in {'auto', 'none', 'required'} else json.loads(tool_choice)

    if openai_user is not None:
      args["user"] = openai_user

    response = client.chat.completions.create(
      model=model
    , messages=messages_1
    , stream=False
    , **args
    )

    return response.model_dump_json()
$python$
language plpython3u volatile parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

------------------------------------------------------------------------------------
-- openai_chat_complete_simple
-- simple chat completion that only requires a message and only returns the response
create or replace function ai.openai_chat_complete_simple
( message text
, api_key text default null
, api_key_name text default null
) returns text
as $$
declare
    model text := 'gpt-4o';
    messages jsonb;
begin
    messages := pg_catalog.jsonb_build_array(
        pg_catalog.jsonb_build_object('role', 'system', 'content', 'you are a helpful assistant'),
        pg_catalog.jsonb_build_object('role', 'user', 'content', message)
    );
    return ai.openai_chat_complete(model, messages, api_key, api_key_name)
        operator(pg_catalog.->)'choices'
        operator(pg_catalog.->)0
        operator(pg_catalog.->)'message'
        operator(pg_catalog.->>)'content';
end;
$$ language plpgsql volatile parallel safe security invoker
set search_path to pg_catalog, pg_temp
;

-------------------------------------------------------------------------------
-- openai_moderate
-- classify text as potentially harmful or not
-- https://platform.openai.com/docs/api-reference/moderations/create
create or replace function ai.openai_moderate
( model text
, input_text text
, api_key text default null
, api_key_name text default null
, base_url text default null
) returns jsonb
as $python$
    #ADD-PYTHON-LIB-DIR
    import ai.openai
    import ai.secrets
    api_key_resolved = ai.secrets.get_secret(plpy, api_key, api_key_name, ai.openai.DEFAULT_KEY_NAME, SD)
    client = ai.openai.make_client(plpy, api_key_resolved, base_url)
    moderation = client.moderations.create(input=input_text, model=model)
    return moderation.model_dump_json()
$python$
language plpython3u immutable parallel safe security invoker
set search_path to pg_catalog, pg_temp
;
