import streamlit as st


def render_jira(state: dict) -> None:
    jira_epic = state.get("jira_epic_key")
    jira_stories = state.get("jira_story_keys", [])

    if not jira_epic and not jira_stories:
        return

    st.divider()
    st.subheader("Jira")
    with st.container(horizontal=True):
        st.metric("Epic", jira_epic or "—", border=True)
        st.metric("Stories/Tasks", len(jira_stories), border=True)
    if jira_stories:
        st.caption("Keys: " + ", ".join(f"`{k}`" for k in jira_stories if k))
