import os.path
import textwrap

import pytest

from tests.lib import (pyversion, path_to_url, requirements_file,
                       _create_test_package_with_subdirectory)
from tests.lib.local_repos import local_checkout


@pytest.mark.network
def test_requirements_file(script):
    """
    Test installing from a requirements file.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    script.scratch_path.join("initools-req.txt").write(textwrap.dedent("""\
        INITools==0.2
        # and something else to test out:
        %s<=%s
        """ % (other_lib_name, other_lib_version)))
    result = script.pip(
        'install', '-r', script.scratch_path / 'initools-req.txt'
    )
    assert (
        script.site_packages / 'INITools-0.2-py%s.egg-info' %
        pyversion in result.files_created
    )
    assert script.site_packages / 'initools' in result.files_created
    assert result.files_created[script.site_packages / other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[script.site_packages / fn].dir


def test_schema_check_in_requirements_file(script):
    """
    Test installing from a requirements file with an invalid vcs schema..

    """
    script.scratch_path.join("file-egg-req.txt").write(
        "\n%s\n" % (
            "git://github.com/alex/django-fixture-generator.git"
            "#egg=fixture_generator"
        )
    )

    with pytest.raises(AssertionError):
        script.pip(
            "install", "-vvv", "-r", script.scratch_path / "file-egg-req.txt"
        )


def test_relative_requirements_file(script, data):
    """
    Test installing from a requirements file with a relative path with an
    egg= definition..

    """
    url = path_to_url(
        os.path.join(data.root, "packages", "..", "packages", "FSPkg")
    ) + '#egg=FSPkg'
    script.scratch_path.join("file-egg-req.txt").write(textwrap.dedent("""\
        %s
        """ % url))
    result = script.pip(
        'install', '-vvv', '-r', script.scratch_path / 'file-egg-req.txt'
    )
    assert (
        script.site_packages / 'FSPkg-0.1.dev0-py%s.egg-info' % pyversion
    ) in result.files_created, str(result)
    assert (script.site_packages / 'fspkg') in result.files_created, (
        str(result.stdout)
    )


@pytest.mark.network
def test_multiple_requirements_files(script, tmpdir):
    """
    Test installing from multiple nested requirements files.

    """
    other_lib_name, other_lib_version = 'anyjson', '0.3'
    script.scratch_path.join("initools-req.txt").write(
        textwrap.dedent("""
            -e %s@10#egg=INITools-dev
            -r %s-req.txt
        """) %
        (
            local_checkout(
                'svn+http://svn.colorstudy.com/INITools/trunk',
                tmpdir.join("cache"),
            ),
            other_lib_name
        ),
    )
    script.scratch_path.join("%s-req.txt" % other_lib_name).write(
        "%s<=%s" % (other_lib_name, other_lib_version)
    )
    result = script.pip(
        'install', '-r', script.scratch_path / 'initools-req.txt'
    )
    assert result.files_created[script.site_packages / other_lib_name].dir
    fn = '%s-%s-py%s.egg-info' % (other_lib_name, other_lib_version, pyversion)
    assert result.files_created[script.site_packages / fn].dir
    assert script.venv / 'src' / 'initools' in result.files_created


def test_package_in_constraints_and_dependencies(script, data):
    script.scratch_path.join("constraints.txt").write(
        "TopoRequires2==0.0.1\nTopoRequires==0.0.1"
    )
    result = script.pip('install', '--no-index', '-f',
                        data.find_links, '-c', script.scratch_path /
                        'constraints.txt', 'TopoRequires2')
    assert 'installed TopoRequires-0.0.1' in result.stdout


def test_multiple_constraints_files(script, data):
    script.scratch_path.join("outer.txt").write("-c inner.txt")
    script.scratch_path.join("inner.txt").write(
        "Upper==1.0")
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'outer.txt', 'Upper')
    assert 'installed Upper-1.0' in result.stdout


def test_respect_order_in_requirements_file(script, data):
    script.scratch_path.join("frameworks-req.txt").write(textwrap.dedent("""\
        parent
        child
        simple
        """))

    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-r',
        script.scratch_path / 'frameworks-req.txt'
    )

    downloaded = [line for line in result.stdout.split('\n')
                  if 'Collecting' in line]

    assert 'parent' in downloaded[0], (
        'First download should be "parent" but was "%s"' % downloaded[0]
    )
    assert 'child' in downloaded[1], (
        'Second download should be "child" but was "%s"' % downloaded[1]
    )
    assert 'simple' in downloaded[2], (
        'Third download should be "simple" but was "%s"' % downloaded[2]
    )


def test_install_local_editable_with_extras(script, data):
    to_install = data.packages.join("LocalExtras")
    res = script.pip(
        'install', '-e', to_install + '[bar]', '--process-dependency-links',
        expect_error=False,
        expect_stderr=True,
    )
    assert script.site_packages / 'easy-install.pth' in res.files_updated, (
        str(res)
    )
    assert (
        script.site_packages / 'LocalExtras.egg-link' in res.files_created
    ), str(res)
    assert script.site_packages / 'simple' in res.files_created, str(res)


@pytest.mark.network
def test_install_collected_dependancies_first(script):
    result = script.pip(
        'install', 'paramiko',
    )
    text = [line for line in result.stdout.split('\n')
            if 'Installing' in line][0]
    assert text.endswith('paramiko')


@pytest.mark.network
def test_install_local_editable_with_subdirectory(script):
    version_pkg_path = _create_test_package_with_subdirectory(script,
                                                              'version_subdir')
    result = script.pip(
        'install', '-e',
        '%s#egg=version_subpkg&subdirectory=version_subdir' %
        ('git+file://%s' % version_pkg_path,)
    )

    result.assert_installed('version-subpkg', sub_dir='version_subdir')


def test_user_with_prefix_in_pydistutils_cfg(script, data, virtualenv):
    virtualenv.system_site_packages = True
    homedir = script.environ["HOME"]
    script.scratch_path.join("bin").mkdir()
    with open(os.path.join(homedir, ".pydistutils.cfg"), "w") as cfg:
        cfg.write(textwrap.dedent("""
            [install]
            prefix=%s""" % script.scratch_path))

    result = script.pip('install', '--user', '--no-index', '-f',
                        data.find_links, 'requiresupper')
    assert 'installed requiresupper' in result.stdout


def test_nowheel_user_with_prefix_in_pydistutils_cfg(script, data, virtualenv):
    virtualenv.system_site_packages = True
    homedir = script.environ["HOME"]
    script.scratch_path.join("bin").mkdir()
    with open(os.path.join(homedir, ".pydistutils.cfg"), "w") as cfg:
        cfg.write(textwrap.dedent("""
            [install]
            prefix=%s""" % script.scratch_path))

    result = script.pip('install', '--no-use-wheel', '--user', '--no-index',
                        '-f', data.find_links, 'requiresupper')
    assert 'installed requiresupper' in result.stdout


def test_install_option_in_requirements_file(script, data, virtualenv):
    """
    Test --install-option in requirements file overrides same option in cli
    """

    script.scratch_path.join("home1").mkdir()
    script.scratch_path.join("home2").mkdir()

    script.scratch_path.join("reqs.txt").write(
        textwrap.dedent(
            """simple --install-option='--home=%s'"""
            % script.scratch_path.join("home1")))

    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-r',
        script.scratch_path / 'reqs.txt',
        '--install-option=--home=%s' % script.scratch_path.join("home2"),
        expect_stderr=True)

    package_dir = script.scratch / 'home1' / 'lib' / 'python' / 'simple'
    assert package_dir in result.files_created


def test_constraints_not_installed_by_default(script, data):
    script.scratch_path.join("c.txt").write("requiresupper")
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'c.txt', 'Upper')
    assert 'requiresupper' not in result.stdout


def test_constraints_only_causes_error(script, data):
    script.scratch_path.join("c.txt").write("requiresupper")
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'c.txt', expect_error=True)
    assert 'installed requiresupper' not in result.stdout


def test_constraints_local_editable_install_causes_error(script, data):
    script.scratch_path.join("constraints.txt").write(
        "singlemodule==0.0.0"
    )
    to_install = data.src.join("singlemodule")
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'constraints.txt', '-e',
        to_install, expect_error=True)
    assert 'Could not satisfy constraints for' in result.stderr


def test_constraints_local_install_causes_error(script, data):
    script.scratch_path.join("constraints.txt").write(
        "singlemodule==0.0.0"
    )
    to_install = data.src.join("singlemodule")
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'constraints.txt',
        to_install, expect_error=True)
    assert 'Could not satisfy constraints for' in result.stderr


def test_constraints_constrain_to_local_editable(script, data):
    to_install = data.src.join("singlemodule")
    script.scratch_path.join("constraints.txt").write(
        "-e file://%s#egg=singlemodule" % to_install
    )
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'constraints.txt', 'singlemodule')
    assert 'Running setup.py develop for singlemodule' in result.stdout


def test_constraints_constrain_to_local(script, data):
    to_install = data.src.join("singlemodule")
    script.scratch_path.join("constraints.txt").write(
        "file://%s#egg=singlemodule" % to_install
    )
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'constraints.txt', 'singlemodule')
    assert 'Running setup.py install for singlemodule' in result.stdout


def test_constrained_to_url_install_same_url(script, data):
    to_install = data.src.join("singlemodule")
    script.scratch_path.join("constraints.txt").write(
        "file://%s#egg=singlemodule" % to_install
    )
    result = script.pip(
        'install', '--no-index', '-f', data.find_links, '-c',
        script.scratch_path / 'constraints.txt', to_install)
    assert 'Running setup.py install for singlemodule' in result.stdout


@pytest.mark.network
def test_double_install_spurious_hash_mismatch(script, tmpdir):
    """Make sure installing the same hashed sdist twice doesn't throw hash
    mismatch errors.

    Really, this is a test that we disable reads from the wheel cache in
    hash-checking mode. Locally, implicitly built wheels of sdists obviously
    have different hashes from the original archives. Comparing against those
    causes spurious mismatch errors.

    """
    script.pip('install', 'wheel')  # Otherwise, it won't try to build wheels.
    with requirements_file('simple==1.0 --hash=sha256:393043e672415891885c9a2a'
                           '0929b1af95fb866d6ca016b42d2e6ce53619b653',
                           tmpdir) as reqs_file:
        # Install a package (and build its wheel):
        result = script.pip_install_local(
            '-r', reqs_file.abspath, expect_error=False)
        assert 'Successfully installed simple-1.0' in str(result)

        # Uninstall it:
        script.pip('uninstall', '-y', 'simple', expect_error=False)

        # Then install it again. We should not hit a hash mismatch, and the
        # package should install happily.
        result = script.pip_install_local(
            '-r', reqs_file.abspath, expect_error=False)
        assert 'Successfully installed simple-1.0' in str(result)
