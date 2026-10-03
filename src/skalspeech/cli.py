import typer

from .commands.align import align_command
from .commands.convert import convert_command
from .commands.csv_commands import csv_app
from .commands.environment import environment_app
from .commands.mfa import mfa_command
from .commands.slice import slice_command
from .version import version_command

app = typer.Typer(help="Tools for speech recordings and Praat TextGrids.")

app.command("version")(version_command)
app.command("slice")(slice_command)
app.command(
	"align",
	context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)(align_command)
app.command(
    "mfa",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)(mfa_command)
app.command("convert")(convert_command)
app.command("textgrid-to-csv")(convert_command)
app.add_typer(csv_app, name="csv")
app.add_typer(environment_app, name="environment")
