import os
import sys
import tempfile
from thoth.app.utils import str_to_bool
from thoth.app.arguments import parse_args
from thoth.app.analyzer import all_analyzers
from thoth.app.analyzer.abstract_analyzer import category_classification_text
from thoth.app.disassembler.disassembler import Disassembler
from thoth.app.starknet.starknet import StarkNet


def main() -> int:
    """Main function of Thoth

    Returns:
        Int: Return 0
    """
    args = parse_args()
    if (args.call or args.cfg) and ("view" not in args):
        print("Need to set -view option")
        sys.exit()

    # Show analyzers help
    if args.analyzers_help is not None:
        if args.analyzers_help:
            for analyzer_name in args.analyzers_help:
                analyzer = [
                    analyzer for analyzer in all_analyzers if analyzer.ARGUMENT == analyzer_name
                ][0]
                analyzer._print_help()
            return 0
        else:
            for analyzer in all_analyzers:
                analyzer._print_help()
            return 0

    # Load compiled contract from a file
    if args.contract == "local":
        file = args.path.name
        filename = os.path.basename(args.path.name).split(".")[0]
    # Load compiled contract from starknet API
    else:
        try:
            contract = StarkNet(args.network).get_full_contract(args.address)
        except Exception as e:
            print(e)
            exit()
        file = tempfile.NamedTemporaryFile().name
        with open(file, "w") as f:
            f.write(contract)
        filename = args.address

    disassembler = Disassembler(file, color=args.color)

    if args.verbose:
        disassembler.dump_json()

    # Decompiler
    if args.decompile and args.analyzers is None:
        print(disassembler.decompiler())
        if args.output:
            output = Disassembler(file, color=False).decompiler()
            with args.output as output_file:
                output_file.write(output)
    # Disassembler
    elif args.disassembly and args.analyzers is None:
        print(disassembler.print_disassembly())
        if args.output:
            output = Disassembler(file, color=False).print_disassembly()
            with args.output as output_file:
                output_file.write(output)

    format = "pdf" if args.format is None else str(args.format)

    # print call flow graph
    if args.call:
        disassembler.print_call_flow_graph(
            folder=args.output_callgraph_folder,
            filename=filename,
            format=format,
            view=str_to_bool(args.view),
        )

    # print CFG
    if args.cfg:
        if args.color:
            disassembler = Disassembler(file, color=False)
        disassembler.print_cfg(
            folder=args.output_cfg_folder,
            filename=filename,
            format=format,
            function_name=args.function,
            view=str_to_bool(args.view),
        )

    if args.analyzers is None:
        return 0

    # Find selected analyzers
    analyzers_names = [analyzer.ARGUMENT for analyzer in all_analyzers]
    selected_analyzers = []

    if args.analyzers:
        selected_analyzers = []
        for analyzer_name in args.analyzers:
            # Select a single analyzer
            if analyzer_name in analyzers_names:
                selected_analyzers.append(
                    [analyzer for analyzer in all_analyzers if analyzer.ARGUMENT == analyzer_name][
                        0
                    ]
                )
            # Select a whole category
            else:
                selected_category = [
                    k
                    for k, v in category_classification_text.items()
                    if v == analyzer_name.capitalize()
                ][0]
                selected_analyzers += [
                    analyzer for analyzer in all_analyzers if analyzer.CATEGORY == selected_category
                ]
    # Select all analyzers by default
    else:
        selected_analyzers = all_analyzers

    # Run analyzers
    for analyzer in selected_analyzers:
        a = analyzer(disassembler, color=args.color)
        a._detect()
        a._print()

    selected_analyzers_count = len(selected_analyzers)
    print(
        "\n[+] %s analyser%s %s run"
        % (
            selected_analyzers_count,
            "s" if selected_analyzers_count > 1 else "",
            "were" if selected_analyzers_count > 1 else "was",
        )
    )
    return 0
