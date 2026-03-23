при экспорте всех файлов сейчас беруться все файлы из директории экспорта и архивируются. мне нужно взять только те файлы, в которых указана ревизия которую я указал в UI
в секции Admin — Quick Sync - оставь только задачи на tag, document и property values
на странице tag register если филтрую по полю а потом сбрасываю фильтр то появляется такое сообшение:
streamlit.errors.StreamlitAPIException: st.session_state.tr_filter cannot be modified after the widget with key tr_filter is instantiated.

Traceback:
File "/app/ui/app.py", line 167, in <module>
    ALL_PAGES[st.session_state["page"]].render()
File "/app/ui/pages/tag_register.py", line 173, in render
    st.session_state["tr_filter"] = ""
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/streamlit/runtime/metrics_util.py", line 409, in wrapped_func
    result = non_optional_func(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/usr/local/lib/python3.12/site-packages/streamlit/runtime/state/session_state_proxy.py", line 113, in __setitem__
    get_session_state()[key] = value
    ~~~~~~~~~~~~~~~~~~~^^^^^
File "/usr/local/lib/python3.12/site-packages/streamlit/runtime/state/safe_session_state.py", line 99, in __setitem__
    self._state[key] = value
    ~~~~~~~~~~~^^^^^
File "/usr/local/lib/python3.12/site-packages/streamlit/runtime/state/session_state.py", line 516, in __setitem__
    raise StreamlitAPIException(

