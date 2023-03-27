import hashlib
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains.base import Chain
from langchain.chains.llm import LLMChain
from langchain.llms.openai import BaseOpenAI, OpenAIChat
from langchain.schema import AgentAction, AgentFinish, LLMResult


def import_wandb() -> Any:
    try:
        import wandb  # noqa: F401
    except ImportError:
        raise ImportError(
            "To use the wandb callback manager you need to have the `wandb` python "
            "package installed. Please install it with `pip install wandb`"
        )
    return wandb


def import_spacy() -> Any:
    try:
        import spacy  # noqa: F401
    except ImportError:
        raise ImportError(
            "To use the wandb callback manager you need to have the `spacy` python "
            "package installed. Please install it with `pip install spacy`"
        )
    return spacy


def import_pandas() -> Any:
    try:
        import pandas  # noqa: F401
    except ImportError:
        raise ImportError(
            "To use the wandb callback manager you need to have the `pandas` python "
            "package installed. Please install it with `pip install pandas`"
        )
    return pandas


def import_textstat() -> Any:
    try:
        import textstat  # noqa: F401
    except ImportError:
        raise ImportError(
            "To use the wandb callback manager you need to have the `textstat` python "
            "package installed. Please install it with `pip install textstat`"
        )
    return textstat


def _flatten_dict(
    nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "_"
) -> Iterable[Tuple[str, Any]]:
    """
    Generator that yields flattened items from a nested dictionary for a flat dict.

    Parameters:
        nested_dict (dict): The nested dictionary to flatten.
        parent_key (str): The prefix to prepend to the keys of the flattened dict.
        sep (str): The separator to use between the parent key and the key of the
            flattened dictionary.

    Yields:
        (str, any): A key-value pair from the flattened dictionary.
    """
    for key, value in nested_dict.items():
        new_key = parent_key + sep + key if parent_key else key
        if isinstance(value, dict):
            yield from _flatten_dict(value, new_key, sep)
        else:
            yield new_key, value


def flatten_dict(
    nested_dict: Dict[str, Any], parent_key: str = "", sep: str = "_"
) -> Dict[str, Any]:
    """Flattens a nested dictionary into a flat dictionary.

    Parameters:
        nested_dict (dict): The nested dictionary to flatten.
        parent_key (str): The prefix to prepend to the keys of the flattened dict.
        sep (str): The separator to use between the parent key and the key of the
            flattened dictionary.

    Returns:
        (dict): A flat dictionary.

    """
    flat_dict = {k: v for k, v in _flatten_dict(nested_dict, parent_key, sep)}
    return flat_dict


def hash_string(s: str) -> str:
    """Hash a string using sha1.

    Parameters:
        s (str): The string to hash.

    Returns:
        (str): The hashed string.
    """
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def load_json_to_dict(json_path: Union[str, Path]) -> dict:
    """Load json file to a dictionary.

    Parameters:
        json_path (str): The path to the json file.

    Returns:
        (dict): The dictionary representation of the json file.
    """
    with open(json_path, "r") as f:
        data = json.load(f)
    return data


def analyze_text(
    text: str,
    complexity_metrics: bool = True,
    visualize: bool = True,
    nlp: Any = None,
    output_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """Analyze text using textstat and spacy.

    Parameters:
        text (str): The text to analyze.
        complexity_metrics (bool): Whether to compute complexity metrics.
        visualize (bool): Whether to visualize the text.
        nlp (spacy.lang): The spacy language model to use for visualization.
        output_dir (str): The directory to save the visualization files to.

    Returns:
        (dict): A dictionary containing the complexity metrics and visualization
            files serialized in a wandb.Html element.
    """
    resp = {}
    textstat = import_textstat()
    wandb = import_wandb()
    spacy = import_spacy()
    if complexity_metrics:
        text_complexity_metrics = {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
            "smog_index": textstat.smog_index(text),
            "coleman_liau_index": textstat.coleman_liau_index(text),
            "automated_readability_index": textstat.automated_readability_index(text),
            "dale_chall_readability_score": textstat.dale_chall_readability_score(text),
            "difficult_words": textstat.difficult_words(text),
            "linsear_write_formula": textstat.linsear_write_formula(text),
            "gunning_fog": textstat.gunning_fog(text),
            "text_standard": textstat.text_standard(text),
            "fernandez_huerta": textstat.fernandez_huerta(text),
            "szigriszt_pazos": textstat.szigriszt_pazos(text),
            "gutierrez_polini": textstat.gutierrez_polini(text),
            "crawford": textstat.crawford(text),
            "gulpease_index": textstat.gulpease_index(text),
            "osman": textstat.osman(text),
        }
        resp.update(text_complexity_metrics)

    if visualize and nlp and output_dir is not None:
        doc = nlp(text)

        dep_out = spacy.displacy.render(  # type: ignore
            doc, style="dep", jupyter=False, page=True
        )
        dep_output_path = Path(output_dir, hash_string(f"dep-{text}") + ".html")
        dep_output_path.open("w", encoding="utf-8").write(dep_out)

        ent_out = spacy.displacy.render(  # type: ignore
            doc, style="ent", jupyter=False, page=True
        )
        ent_output_path = Path(output_dir, hash_string(f"ent-{text}") + ".html")
        ent_output_path.open("w", encoding="utf-8").write(ent_out)

        text_visualizations = {
            "dependency_tree": wandb.Html(str(dep_output_path)),
            "entities": wandb.Html(str(ent_output_path)),
        }
        resp.update(text_visualizations)

    return resp


def construct_html_from_prompt_and_generation(prompt: str, generation: str) -> Any:
    """Construct an html element from a prompt and a generation.

    Parameters:
        prompt (str): The prompt.
        generation (str): The generation.

    Returns:
        (wandb.Html): The html element."""
    wandb = import_wandb()
    formatted_prompt = prompt.replace("\n", "<br>")
    formatted_generation = generation.replace("\n", "<br>")

    style = """<style type="text/css">
    body {
        font-family: Arial, sans-serif;
        background-color: #f4f4f4;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        margin: 0;
    }

    .chat-container {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 20px;
        max-width: 600px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }

    .chat-message {
        display: inline-block;
        padding: 10px 15px;
        border-radius: 18px;
        margin-bottom: 8px;
        max-width: 80%;
        word-wrap: break-word;
    }

    .user {
        background-color: #007bff;
        color: #ffffff;
        align-self: flex-end;
        border-bottom-right-radius: 4px;
    }

    .chatbot {
        background-color: #e6e6e6;
        color: #333333;
        align-self: flex-start;
        border-bottom-left-radius: 4px;
    }
</style>
    """

    body = f"""<body>
    <div class="chat-container">
        <div class="chat-message user">{formatted_prompt}</div>
        <div class="chat-message chatbot">{formatted_generation}</div>
    </div>
</body>
    """

    return wandb.Html(
        f"""
    <html>
        <head>
            {style}
        </head>
        {body}
    </html>
    """,
        inject=False,
    )


class BaseMetadataCallbackHandler:
    """This class handles the metadata and associated function states for callbacks.

    Attributes:
        step (int): The current step.
        starts (int): The number of times the start method has been called.
        ends (int): The number of times the end method has been called.
        errors (int): The number of times the error method has been called.
        text_ctr (int): The number of times the text method has been called.
        ignore_llm_ (bool): Whether to ignore llm callbacks.
        ignore_chain_ (bool): Whether to ignore chain callbacks.
        ignore_agent_ (bool): Whether to ignore agent callbacks.
        always_verbose_ (bool): Whether to always be verbose.
        chain_starts (int): The number of times the chain start method has been called.
        chain_ends (int): The number of times the chain end method has been called.
        llm_starts (int): The number of times the llm start method has been called.
        llm_ends (int): The number of times the llm end method has been called.
        llm_streams (int): The number of times the text method has been called.
        tool_starts (int): The number of times the tool start method has been called.
        tool_ends (int): The number of times the tool end method has been called.
        agent_ends (int): The number of times the agent end method has been called.
        on_llm_start_records (list): A list of records of the on_llm_start method.
        on_llm_token_records (list): A list of records of the on_llm_token method.
        on_llm_end_records (list): A list of records of the on_llm_end method.
        on_chain_start_records (list): A list of records of the on_chain_start method.
        on_chain_end_records (list): A list of records of the on_chain_end method.
        on_tool_start_records (list): A list of records of the on_tool_start method.
        on_tool_end_records (list): A list of records of the on_tool_end method.
        on_agent_finish_records (list): A list of records of the on_agent_end method.
    """

    def __init__(self) -> None:
        self.step = 0

        self.starts = 0
        self.ends = 0
        self.errors = 0
        self.text_ctr = 0

        self.ignore_llm_ = False
        self.ignore_chain_ = False
        self.ignore_agent_ = False
        self.always_verbose_ = False

        self.chain_starts = 0
        self.chain_ends = 0

        self.llm_starts = 0
        self.llm_ends = 0
        self.llm_streams = 0

        self.tool_starts = 0
        self.tool_ends = 0

        self.agent_ends = 0

        self.on_llm_start_records: list = []
        self.on_llm_token_records: list = []
        self.on_llm_end_records: list = []

        self.on_chain_start_records: list = []
        self.on_chain_end_records: list = []

        self.on_tool_start_records: list = []
        self.on_tool_end_records: list = []

        self.on_text_records: list = []
        self.on_agent_finish_records: list = []
        self.on_agent_action_records: list = []

    @property
    def always_verbose(self) -> bool:
        """Whether to call verbose callbacks even if verbose is False."""
        return self.always_verbose_

    @property
    def ignore_llm(self) -> bool:
        """Whether to ignore LLM callbacks."""
        return self.ignore_llm_

    @property
    def ignore_chain(self) -> bool:
        """Whether to ignore chain callbacks."""
        return self.ignore_chain_

    @property
    def ignore_agent(self) -> bool:
        """Whether to ignore agent callbacks."""
        return self.ignore_agent_

    def get_custom_callback_meta(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "starts": self.starts,
            "ends": self.ends,
            "errors": self.errors,
            "text_ctr": self.text_ctr,
            "chain_starts": self.chain_starts,
            "chain_ends": self.chain_ends,
            "llm_starts": self.llm_starts,
            "llm_ends": self.llm_ends,
            "llm_streams": self.llm_streams,
            "tool_starts": self.tool_starts,
            "tool_ends": self.tool_ends,
            "agent_ends": self.agent_ends,
        }

    def reset_callback_meta(self) -> None:
        """Reset the callback metadata."""
        self.step = 0

        self.starts = 0
        self.ends = 0
        self.errors = 0
        self.text_ctr = 0

        self.ignore_llm_ = False
        self.ignore_chain_ = False
        self.ignore_agent_ = False
        self.always_verbose_ = False

        self.chain_starts = 0
        self.chain_ends = 0

        self.llm_starts = 0
        self.llm_ends = 0
        self.llm_streams = 0

        self.tool_starts = 0
        self.tool_ends = 0

        self.agent_ends = 0

        self.on_llm_start_records = []
        self.on_llm_token_records = []
        self.on_llm_end_records = []

        self.on_chain_start_records = []
        self.on_chain_end_records = []

        self.on_tool_start_records = []
        self.on_tool_end_records = []

        self.on_text_records = []
        self.on_agent_finish_records = []
        self.on_agent_action_records = []
        return None


class WandbCallbackHandler(BaseMetadataCallbackHandler, BaseCallbackHandler):
    """Callback Handler that logs to Weights and Biases.

    Parameters:
        job_type (str): The type of job.
        project (str): The project to log to.
        entity (str): The entity to log to.
        tags (list): The tags to log.
        group (str): The group to log to.
        name (str): The name of the run.
        notes (str): The notes to log.
        visualize (bool): Whether to visualize the run.
        complexity_metrics (bool): Whether to log complexity metrics.
        stream_logs (bool): Whether to stream callback actions to W&B

    This handler will utilize the associated callback method called and formats
    the input of each callback function with metadata regarding the state of LLM run,
    and adds the response to the list of records for both the {method}_records and
    action. It then logs the response using the run.log() method to Weights and Biases.
    """

    def __init__(
        self,
        job_type: Optional[str] = None,
        project: Optional[str] = "langchain_callback_demo",
        entity: Optional[str] = None,
        tags: Optional[Sequence] = None,
        group: Optional[str] = None,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        visualize: bool = False,
        complexity_metrics: bool = False,
        stream_logs: bool = False,
    ) -> None:
        """Initialize callback handler."""

        wandb = import_wandb()
        import_pandas()
        import_textstat()
        spacy = import_spacy()
        super().__init__()

        self.job_type = job_type
        self.project = project
        self.entity = entity
        self.tags = tags
        self.group = group
        self.name = name
        self.notes = notes
        self.visualize = visualize
        self.complexity_metrics = complexity_metrics
        self.stream_logs = stream_logs

        self.temp_dir = tempfile.TemporaryDirectory()
        self.run: wandb.sdk.wandb_run.Run = wandb.init(  # type: ignore
            job_type=self.job_type,
            project=self.project,
            entity=self.entity,
            tags=self.tags,
            group=self.group,
            name=self.name,
            notes=self.notes,
        )
        warning = (
            "The wandb callback is currently in beta and is subject to change "
            "based on updates to `langchain`. Please report any issues to "
            "https://github.com/wandb/wandb/issues with the tag `langchain`."
        )
        wandb.termwarn(
            warning,
            repeat=False,
        )
        self.callback_columns: list = []
        self.action_records: list = []
        self.complexity_metrics = complexity_metrics
        self.visualize = visualize
        self.nlp = spacy.load("en_core_web_sm")
        self.input_keys: Set[str] = set()

    def _init_resp(self) -> Dict:
        return {k: None for k in self.callback_columns}

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts."""
        self.step += 1
        self.llm_starts += 1
        self.starts += 1

        resp = self._init_resp()
        resp.update({"action": "on_llm_start"})
        resp.update(flatten_dict(serialized))
        resp.update(self.get_custom_callback_meta())

        for prompt in prompts:
            prompt_resp = deepcopy(resp)
            prompt_resp["prompts"] = prompt
            self.on_llm_start_records.append(prompt_resp)
            self.action_records.append(prompt_resp)
            if self.stream_logs:
                self.run.log(prompt_resp)

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Run when LLM generates a new token."""
        self.step += 1
        self.llm_streams += 1

        resp = self._init_resp()
        resp.update({"action": "on_llm_new_token", "token": token})
        resp.update(self.get_custom_callback_meta())

        self.on_llm_token_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        self.step += 1
        self.llm_ends += 1
        self.ends += 1

        resp = self._init_resp()
        resp.update({"action": "on_llm_end"})
        resp.update(flatten_dict(response.llm_output or {}))
        resp.update(self.get_custom_callback_meta())

        for generations in response.generations:
            for generation in generations:
                generation_resp = deepcopy(resp)
                generation_resp.update(flatten_dict(generation.dict()))
                generation_resp.update(
                    analyze_text(
                        generation.text,
                        complexity_metrics=self.complexity_metrics,
                        visualize=self.visualize,
                        nlp=self.nlp,
                        output_dir=self.temp_dir.name,
                    )
                )
                self.on_llm_end_records.append(generation_resp)
                self.action_records.append(generation_resp)
                if self.stream_logs:
                    self.run.log(generation_resp)

    def on_llm_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when LLM errors."""
        self.step += 1
        self.errors += 1

    def on_chain_start(
        self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        self.step += 1
        self.chain_starts += 1
        self.starts += 1

        resp = self._init_resp()
        resp.update({"action": "on_chain_start"})
        resp.update(flatten_dict(serialized))
        resp.update(flatten_dict(inputs))
        resp.update(self.get_custom_callback_meta())

        self.on_chain_start_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

        self.input_keys.update(inputs.keys())

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""
        self.step += 1
        self.chain_ends += 1
        self.ends += 1

        resp = self._init_resp()
        resp.update({"action": "on_chain_end"})
        resp.update(flatten_dict(outputs))
        resp.update(self.get_custom_callback_meta())

        self.on_chain_end_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def on_chain_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when chain errors."""
        self.step += 1
        self.errors += 1

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running."""
        self.step += 1
        self.tool_starts += 1
        self.starts += 1

        resp = self._init_resp()
        resp.update({"action": "on_tool_start", "input_str": input_str})
        resp.update(flatten_dict(serialized))
        resp.update(self.get_custom_callback_meta())

        self.on_tool_start_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        self.step += 1
        self.tool_ends += 1
        self.ends += 1

        resp = self._init_resp()
        resp.update({"action": "on_tool_end", "output": output})
        resp.update(self.get_custom_callback_meta())

        self.on_tool_end_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Run when tool errors."""
        self.step += 1
        self.errors += 1

    def on_text(self, text: str, **kwargs: Any) -> None:
        """
        Run when agent is ending.
        """
        self.step += 1
        self.text_ctr += 1

        resp = self._init_resp()
        resp.update({"action": "on_text", "text": text})
        resp.update(self.get_custom_callback_meta())

        self.on_text_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run when agent ends running."""
        self.step += 1
        self.agent_ends += 1
        self.ends += 1

        resp = self._init_resp()
        resp.update(
            {
                "action": "on_agent_finish",
                "output": finish.return_values["output"],
                "log": finish.log,
            }
        )
        resp.update(self.get_custom_callback_meta())

        self.on_agent_finish_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        """Run on agent action."""
        self.step += 1
        self.tool_starts += 1
        self.starts += 1

        resp = self._init_resp()
        resp.update(
            {
                "action": "on_agent_action",
                "tool": action.tool,
                "tool_input": action.tool_input,
                "log": action.log,
            }
        )
        resp.update(self.get_custom_callback_meta())
        self.on_agent_action_records.append(resp)
        self.action_records.append(resp)
        if self.stream_logs:
            self.run.log(resp)

    def _create_common_session_analysis_df(self) -> Any:
        """Create a dataframe with all the information from the session."""
        pd = import_pandas()
        on_llm_start_records_df = pd.DataFrame(self.on_llm_start_records)
        on_llm_end_records_df = pd.DataFrame(self.on_llm_end_records)

        llm_input_prompts_df = (
            on_llm_start_records_df[["step", "prompts", "name"]]
            .dropna(axis=1)
            .rename({"step": "prompt_step"}, axis=1)
        )
        complexity_metrics_columns = []
        visualizations_columns = []

        if self.complexity_metrics:
            complexity_metrics_columns = [
                "flesch_reading_ease",
                "flesch_kincaid_grade",
                "smog_index",
                "coleman_liau_index",
                "automated_readability_index",
                "dale_chall_readability_score",
                "difficult_words",
                "linsear_write_formula",
                "gunning_fog",
                "text_standard",
                "fernandez_huerta",
                "szigriszt_pazos",
                "gutierrez_polini",
                "crawford",
                "gulpease_index",
                "osman",
            ]

        if self.visualize:
            visualizations_columns = ["dependency_tree", "entities"]

        llm_outputs_df = (
            on_llm_end_records_df[
                [
                    "step",
                    "text",
                ]
                + complexity_metrics_columns
                + visualizations_columns
            ]
            .dropna(axis=1)
            .rename({"step": "output_step", "text": "output"}, axis=1)
        )
        session_analysis_df = pd.concat([llm_input_prompts_df, llm_outputs_df], axis=1)
        session_analysis_df["chat_html"] = session_analysis_df[
            ["prompts", "output"]
        ].apply(
            lambda row: construct_html_from_prompt_and_generation(
                row["prompts"], row["output"]
            ),
            axis=1,
        )
        return session_analysis_df

    def flush_tracker(
        self,
        langchain_asset: Any = None,
        reset: bool = True,
        finish: bool = False,
        job_type: Optional[str] = None,
        project: Optional[str] = None,
        entity: Optional[str] = None,
        tags: Optional[Sequence] = None,
        group: Optional[str] = None,
        name: Optional[str] = None,
        notes: Optional[str] = None,
        visualize: Optional[bool] = None,
        complexity_metrics: Optional[bool] = None,
    ) -> None:
        """Flush the tracker and reset the session.

        Args:
            langchain_asset: The langchain asset to save.
            reset: Whether to reset the session.
            finish: Whether to finish the run.
            job_type: The job type.
            project: The project.
            entity: The entity.
            tags: The tags.
            group: The group.
            name: The name.
            notes: The notes.
            visualize: Whether to visualize.
            complexity_metrics: Whether to compute complexity metrics.

            Returns:
                None
        """
        pd = import_pandas()
        wandb = import_wandb()

        table_records = {}

        if len(self.action_records) > 0:
            action_records_table = wandb.Table(
                dataframe=pd.DataFrame(self.action_records)
            )
            table_records["action_records"] = action_records_table
        else:
            wandb.termlog("No actions were run.")

        if (
            len(self.on_llm_start_records) == len(self.on_llm_end_records)
            and len(self.on_llm_start_records) > 0
        ):
            session_analysis_df = self._create_common_session_analysis_df()

            if isinstance(langchain_asset, Chain):
                if len(self.on_chain_start_records) == len(self.on_llm_start_records):
                    chain_inputs = pd.DataFrame(self.on_chain_start_records)[
                        list(self.input_keys)
                    ]
                    session_analysis_df = pd.concat(
                        [chain_inputs, session_analysis_df], axis=1
                    )
                if isinstance(langchain_asset, LLMChain):
                    if isinstance(langchain_asset.llm, (BaseOpenAI, OpenAIChat)):
                        openai_token_info = pd.DataFrame(self.on_llm_end_records)[
                            [
                                "token_usage_total_tokens",
                                "token_usage_prompt_tokens",
                                "token_usage_completion_tokens",
                            ]
                        ]
                        session_analysis_df = pd.concat(
                            [session_analysis_df, openai_token_info], axis=1
                        )

            # TODO: DRY
            if isinstance(langchain_asset.llm, (BaseOpenAI, OpenAIChat)):
                openai_token_info = pd.DataFrame(self.on_llm_end_records)[
                    [
                        "token_usage_total_tokens",
                        "token_usage_prompt_tokens",
                        "token_usage_completion_tokens",
                    ]
                ]
                session_analysis_df = pd.concat(
                    [session_analysis_df, openai_token_info], axis=1
                )

            session_analysis_table = wandb.Table(dataframe=session_analysis_df)
            table_records["session_analysis"] = session_analysis_table
        else:
            wandb.termlog(
                f"Record mismatch: (on_llm_start_records - "
                f"{len(self.on_llm_start_records)}) != (on_llm_end_records "
                f"- {len(self.on_llm_end_records)})"
            )
            wandb.termlog("or")
            wandb.termlog("No records run.")

        self.run.log(table_records)

        if langchain_asset:
            langchain_asset_path = Path(self.temp_dir.name, "model.json")
            model_artifact = wandb.Artifact(name="model", type="model")
            for tab_name, tab in table_records.items():
                model_artifact.add(tab, name=tab_name)
            try:
                langchain_asset.save(langchain_asset_path)
                model_artifact.add_file(str(langchain_asset_path))
                model_meta = load_json_to_dict(langchain_asset_path)
                model_artifact.metadata = model_meta
                self.run.config.update(model_meta)
            except ValueError:
                # TODO: Replace with check of agent as opposed to this try catch
                langchain_asset.save_agent(langchain_asset_path)
                model_artifact.add_file(str(langchain_asset_path))
                model_meta = load_json_to_dict(langchain_asset_path)
                model_artifact.metadata = model_meta
                self.run.config.update(model_meta)
            except NotImplementedError as e:
                wandb.termlog("Could not save model.")
                wandb.termlog(repr(e))
                pass
            self.run.log_artifact(model_artifact)

        if finish or reset:
            self.run.finish()
            self.temp_dir.cleanup()
            self.reset_callback_meta()
        if reset and not finish:
            self.__init__(  # type: ignore
                job_type=job_type if job_type else self.job_type,
                project=project if project else self.project,
                entity=entity if entity else self.entity,
                tags=tags if tags else self.tags,
                group=group if group else self.group,
                name=name if name else self.name,
                notes=notes if notes else self.notes,
                visualize=visualize if visualize else self.visualize,
                complexity_metrics=complexity_metrics
                if complexity_metrics
                else self.complexity_metrics,
            )
