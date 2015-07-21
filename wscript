#!/usr/bin/env python
#
# usage:
#   $ python waf --help
#
# example:
#   $ ./waf distclean configure build
#

from waflib import Options
import sys, os

APPNAME = "dseq"
VERSION = "0.0.1"

top = "."
out = "build"

def options( ctx ):
    ctx.load( "compiler_d" )
    ctx.load( "compiler_c" )

    ctx.add_option( "--debug",
                    action = "store_true",
                    help = ( "disable optimizations and compile with debug symbols" ),
                    default = False,
                    dest = "debug" )

    ctx.add_option( "--release",
                    action = "store_true",
                    help = ( "enable optimizations and compile without debug symbols" ),
                    default = False,
                    dest = "release" )

def configure( ctx ):
    opts = Options.options

    ctx.load( "compiler_d" )
    ctx.load( "compiler_c" )
    ctx.env.append_value( "DFLAGS", "-w" )
    if opts.debug :
        ctx.env.append_value( "DFLAGS", [ "-gc", "-debug" ] )
    else:
        ctx.env.append_value( "DFLAGS", [ "-O", "-release", "-inline", "-boundscheck=off" ] )

    # Check for jack
    if ctx.check_cfg( package = "jack",
                      args = [ "jack >= 0.120.0", "--cflags", "--libs" ],
                      uselib_store = "jack",
                      mandatory = False if sys.platform == "darwin" else True ):
        ctx.define( "HAVE_JACK", 1 )
        ctx.env.DFLAGS.append( "-version=HAVE_JACK" )

    # Configure CoreAudio on OSX
    if sys.platform == "darwin":
        if (ctx.check_cc( framework_name = "CoreAudio", mandatory = False ) and
            ctx.check_cc( framework_name = "AudioUnit", mandatory = False )):
            # Pass OSX frameworks to DMD
            ctx.env.LINKFLAGS_dprogram.extend( [ "-L-framework", "-LCoreAudio", "-L-framework", "-LAudioUnit" ] )
            ctx.env.DFLAGS.append( "-version=HAVE_COREAUDIO" )

    # Check for libsndfile
    ctx.check_cfg( package = "sndfile",
                   args = [ "sndfile >= 1.0.18", "--cflags", "--libs" ],
                   uselib_store = "sndfile",
                   mandatory = True )

    # Check for libsamplerate
    ctx.check_cfg( package = "samplerate",
                   args = [ "samplerate >= 0.1.0", "--cflags", "--libs" ],
                   uselib_store = "samplerate",
                   mandatory = True )

    # Check for rubberband
    if sys.platform == "darwin":
        # rubberband doesn't use pkg-config on OSX, so manual detection is required
        ctx.check_cc( lib = "rubberband", use = "rubberband" )
        ctx.env.append_value( "LIB_rubberband", "rubberband" )
        # assume that rubberband was built against fftw3
        ctx.check_cc( lib = "fftw3" )
        ctx.check_cc( lib = "fftw3f" )
        # rubberband is written in C++
        ctx.check_cc( lib = "stdc++" )
        ctx.env.append_value( "LIB_rubberband", [ "fftw3", "fftw3f", "stdc++" ] )
    else:
        ctx.check_cfg( package = "rubberband",
                       args = [ "rubberband >= 1.8.1", "--cflags", "--libs" ],
                       uselib_store = "rubberband",
                       mandatory = True)

    # Check for aubio
    ctx.check_cfg( package = "aubio",
                   args = [ "aubio >= 0.4.1", "--cflags", "--libs" ],
                   uselib_store = "aubio",
                   mandatory = True )

    # Check for GtkD
    ctx.check_cfg( package = "gtkd-3",
                   args = [ "gtkd-3 >= 3.1.3", "--cflags", "--libs" ],
                   uselib_store = "gtkd",
                   mandatory = True )

    # Configure GtkD on OSX
    if sys.platform == "darwin":
        # Try to fix the output from the gtkd-3 pkg-config entry on OSX
        ctx.env.LIB_gtkd = map(lambda x: x[2:], filter(lambda x: x[:2] == "-l", ctx.env.LIBPATH_gtkd))
        ctx.env.LIBPATH_gtkd = map(lambda x: x[2:], filter(lambda x: x[:2] == "-L", ctx.env.LIBPATH_gtkd))

        # Add flags for GTK-OSX
        home = os.getenv("HOME")
        ctx.env.LIBPATH_gtkd = [ home + "/gtk/inst/lib" ]
        ctx.env.append_value( "LIB_gtkd", [ "gtk-3", "gdk-3", "atk-1.0", "gio-2.0",
                                            "pangocairo-1.0", "gdk_pixbuf-2.0", "cairo-gobject",
                                            "pango-1.0", "cairo", "gobject-2.0", "glib-2.0" ] )

def build( ctx ):
    use_libs = [ "gtkd" ]
    deps_dir = "deps"

    # Build JACK wrapper
    if "HAVE_JACK" in ctx.env.define_key:
        dlang_jack_dir = os.path.join( deps_dir, "jack" )
        ctx.stlib( source = ctx.path.ant_glob( os.path.join( dlang_jack_dir, "**", "*.d" ) ),
                   includes = deps_dir,
                   target = "dlang_jack" )
        use_libs.extend( [ "jack", "dlang_jack" ] )

    # Build CoreAudio wrapper on OSX
    if sys.platform == "darwin":
        ctx.stlib( source = os.path.join( deps_dir, "coreaudio/coreaudio.c" ),
                   target = "coreaudio" )
        use_libs.append( "coreaudio" )
        ctx.env.append_value( "LINKFLAGS_coreaudio", [ "framework", "CoreAudio", "framework", "AudioUnit" ] )

    # Build libsndfile wrapper
    dlang_sndfile_dir = os.path.join( deps_dir, "sndfile" )
    ctx.stlib( source = ctx.path.ant_glob( os.path.join( dlang_sndfile_dir, "**", "*.d" ) ),
               includes = deps_dir,
               target = "dlang_sndfile" )
    use_libs.extend( [ "sndfile", "dlang_sndfile" ] )

    # Build libsamplerate wrapper
    dlang_samplerate_dir = os.path.join( deps_dir, "samplerate" )
    ctx.stlib( source = ctx.path.ant_glob( os.path.join( dlang_samplerate_dir, "**", "*.d" ) ),
               includes = deps_dir,
               target = "dlang_samplerate" )
    use_libs.extend( [ "samplerate", "dlang_samplerate" ] )

    # Build rubberband wrapper
    dlang_rubberband_dir = os.path.join( deps_dir, "rubberband" )
    ctx.stlib( source = ctx.path.ant_glob( os.path.join( dlang_rubberband_dir, "**", "*.d" ) ),
               includes = deps_dir,
               target = "dlang_rubberband" )
    use_libs.extend( [ "rubberband", "dlang_rubberband" ] )

    # Build aubio wrapper
    dlang_aubio_dir = os.path.join( deps_dir, "aubio" )
    ctx.stlib( source = ctx.path.ant_glob( os.path.join( dlang_aubio_dir, "**", "*.d" ) ),
               includes = deps_dir,
               target = "dlang_aubio" )
    use_libs.extend( [ "aubio", "dlang_aubio" ] )

    # Build the executable
    ctx.program( name = APPNAME,
                 target = APPNAME.lower(),
                 source = ctx.path.ant_glob( "src/**/*.d" ),
                 includes = [ "src", deps_dir ],
                 use = use_libs )
