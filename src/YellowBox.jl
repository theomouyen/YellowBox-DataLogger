module YellowBox
using Stromboli
using PyCall
using Gtk

@pyimport pickle


"""
myunpickle:

Reads python pickle file format in julia.
"""
function myunpickle(filename)
    r = nothing
    @pywith pybuiltin("open")(filename,"rb") as f begin
        r = pickle.load(f)
    end
    return r
end
export myunpickle



"""
"""
function get_data()
  path  = open_dialog("Select recording to load")
  file  = basename(filepath)
  fpath =  path[1:findlast(isequal('.'),file)-1]

  data      = myunpickle(fpath * ".pkl")
  audio     = read_audio(fpath * ".wav")
end
export get_data
