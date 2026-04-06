import sys
import types
import argparse
import book

def make_args(**kwargs):
    args = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(args, k, v)
    # Add common flags
    if not hasattr(args, 'verbose'):
        args.verbose = True
    if not hasattr(args, 'debug'):
        args.debug = True
    if not hasattr(args, 'json'):
        args.json = False
    return args

def test_init():
    args = make_args(book_name="testbook3", chapter_count=2, workspace_root=".", config_path=".pkbook/config.json")
    book.Author.run_init(args)

def test_layout():
    args = make_args(book_name="testbook3", gist="Test gist for book", workspace_root=".", config_path=".pkbook/config.json", encoding="utf-8", no_cache=False, no_randomize_thoughts=False, human_in_loop=False, mode="default", chapter_count=3)
    book.Author.run_layout(args)

def test_draft():
    args = make_args(book_name="testbook3", gist="Test gist for book", workspace_root=".", config_path=".pkbook/config.json", encoding="utf-8", no_cache=False)
    book.Author.run_draft(args)

def test_publish():
    args = make_args(book_name="testbook3", workspace_root=".", config_path=".pkbook/config.json", encoding="utf-8", output_path=None)
    book.Author.run_publish(args)

def test_read():
    args = make_args(book_name="testbook3", workspace_root=".", config_path=".pkbook/config.json")
    book.Author.run_read(args)

def run_all():
    test_init()
    test_layout()
    test_draft()
    test_publish()
    test_read()
    print("All direct method tests completed.")

if __name__ == "__main__":
    run_all()
