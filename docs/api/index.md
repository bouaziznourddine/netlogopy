# API reference

Every public name at a glance; each page of this section gives the signatures
and docstrings.

## [`NetLogo` session](netlogo.md)

| Group | Members |
|---|---|
| Session | `NetLogo(model=None, gui=False, netlogo_home=None, java_home=None, jvm_args=(), setup=False)`, `open_model`, `close` / `close_model`, `closed`, `gui`, `model_path`, `netlogo_version` |
| Code | `command(*commands)`, `report(reporter or list)`, `observe(reporter or list)`, `report_java` |
| Simulation | `setup`, `go(times)`, `run_until(condition, max_steps)`, `collect(...)`, `collect_agents(...)`, `agent_table(...)`, `schedule_reporters(...)` |
| Background run | `start(command, interval, max_steps, until)`, `pause`, `resume`, `stop(timeout)`, `halt`, `wait(timeout)`, `hold()`, `running`, `paused`, `steps_run` |
| Ticks | `ticks`, `tick`, `tick_advance`, `reset_ticks`, `clear_ticks` |
| Globals | `globals[...]`, `get_global`, `set_global`, `global_names` |
| World | `min_pxcor`, `max_pxcor`, `min_pycor`, `max_pycor`, `world_width`, `world_height`, `resize_world`, `patch_size`, `set_patch_size`, `wrap_x`, `wrap_y`, `set_topology`, `random_seed`, `new_seed`, `clear_all`, `clear_turtles`, `clear_patches`, `clear_links`, `clear_globals`, `clear_drawing`, `display`, `no_display` |
| Agents | `turtle`, `patch`, `link`, `turtles`, `patches`, `links`, `count`, `ask`, `of`, `create_turtles`, `create_link`, `breeds`, `shapes`, `link_shapes`, `import_shapes`, `set_default_shape` |
| Choosing agents | `any`, `all`, `one_of`, `n_of`, `max_one_of`, `min_one_of`, `max_n_of`, `min_n_of`, `with_max`, `with_min`, `sort_on`, `turtles_on` |
| Random numbers | `random`, `random_float`, `random_normal`, `random_poisson`, `random_exponential`, `random_gamma`, `random_xcor`, `random_ycor`, `random_pxcor`, `random_pycor` |
| Colors, angles | `scale_color`, `shade_of`, `wrap_color`, `extract_rgb`, `extract_hsb`, `approximate_rgb`, `approximate_hsb`, `hsb`, `subtract_headings` |
| Patches | `patch_grid`, `set_patch_grid`, `diffuse`, `import_pcolors`, `import_drawing` |
| Files | `export_view`, `view_png`, `view_array`, `record_gif`, `export_interface`, `export_world`, `import_world`, `export_output`, `export_plot`, `export_all_plots` |
| NetLogo file I/O | `file_open`, `file_close`, `file_close_all`, `file_flush`, `file_delete`, `file_exists`, `file_print`, `file_show`, `file_type`, `file_write`, `file_read`, `file_read_line`, `file_read_characters`, `file_at_end`, `set_current_directory` |
| Output | `show`, `output_print`, `output_show`, `output_type`, `output_write`, `clear_output` |
| Plots | `plot`, `plotxy`, `histogram`, `set_current_plot`, `set_current_plot_pen`, `create_temporary_plot_pen`, `clear_plot`, `clear_all_plots`, `set_plot_pen_color`, `set_plot_pen_mode`, `set_plot_pen_interval`, `plot_pen_up`, `plot_pen_down`, `plot_pen_reset`, `set_histogram_num_bars`, `set_plot_x_range`, `set_plot_y_range`, `auto_plot_on`, `auto_plot_off`, `setup_plots`, `update_plots`, `plot_name`, `plot_pen_exists`, `plot_x_range`, `plot_y_range`, `autoplot` (NetLogo 7) |
| Layouts | `layout_circle`, `layout_spring`, `layout_radial`, `layout_tutte` |
| Observer | `watch`, `follow`, `ride`, `reset_perspective`, `inspect`, `stop_inspecting` |
| Interface widgets (window) | `add_button`, `add_slider`, `add_switch`, `add_chooser`, `add_input`, `add_monitor`, `add_plot`, `add_output`, `add_note`, `press_button` |
| Timer, clock | `reset_timer`, `timer`, `date_and_time`, `beep` |
| Mouse, dialogs (window) | `mouse_down`, `mouse_inside`, `mouse_xcor`, `mouse_ycor`, `user_message`, `user_input`, `user_yes_or_no`, `user_one_of`, `user_file`, `user_new_file`, `user_directory` |

Primitives without a method of their own (maths, lists, strings, control flow, HubNet) are the ones
Python already has; they remain available in any NetLogo code passed to `command()` and `report()`.

## [Agents](agents.md)

| Class | Members |
|---|---|
| all agents | `get`, `set`, `agent[name]`, `get_many`, `ask`, `of`, `alive`, `watch`, `ref` |
| `Turtle` | `who`, `breed`, `set_breed`, `xcor`, `ycor`, `xy`, `heading`, `color`, `size`, `shape`, `label`, `label_color`, `hidden`, `pen_mode`, `pen_size`, `dx`, `dy`; `forward`/`fd`, `back`/`bk`, `right`/`rt`, `left`/`lt`, `jump`, `setxy`, `move_to`, `face`, `facexy`, `home`, `can_move`, `die`, `hide_turtle`/`ht`, `show_turtle`/`st`, `pen_down`/`pd`, `pen_up`/`pu`, `pen_erase`/`pe`, `stamp`, `stamp_erase`, `distance`, `distancexy`, `towards`, `towardsxy`, `patch_here`, `patch_ahead`, `patch_at`, `patch_right_and_ahead`, `patch_left_and_ahead`, `neighbors`, `neighbors4`, `turtles_here`, `in_radius`, `in_cone`, `hatch`, `create_link_with`, `create_link_to`, `create_link_from`, `link_neighbors`, `in_link_neighbors`, `out_link_neighbors`, `my_links`, `my_in_links`, `my_out_links`, `link_with`, `create_links_with`, `create_links_to`, `create_links_from`, `is_link_neighbor`, `is_in_link_neighbor`, `is_out_link_neighbor`, `in_link_from`, `out_link_to`, `uphill`, `uphill4`, `downhill`, `downhill4`, `turtles_at`, `patch_at_heading_and_distance`, `follow`, `ride` |
| `Patch` | `pxcor`, `pycor`, `pcolor`, `plabel`, `plabel_color`; `neighbors`, `neighbors4`, `turtles_here`, `turtles_at`, `patch_at`, `patch_at_heading_and_distance`, `distance`, `distancexy`, `in_radius`, `sprout` |
| `Link` | `end1`, `end2`, `both_ends`, `other_end`, `breed`, `directed`, `color`, `label`, `label_color`, `thickness`, `shape`, `hidden`, `tie_mode`, `length`, `heading`; `die`, `hide_link`, `show_link`, `tie`, `untie` |

## Module

| Name | Purpose |
|---|---|
| `run_experiment`, `parameter_grid` | parameter sweeps |
| `Code`, `to_netlogo` | NetLogo code and literals |
| `colors` | `RED`, `GREEN`, ..., `BASE_COLORS`, `rgb`, `rgba`, `shade` |
| `NetLogoError`, `NetLogoCompileError`, `NetLogoRuntimeError`, `NetLogoNotFoundError` | exceptions |
| `find_netlogo_home`, `netlogo_version`, `jvm_info` | installation details |
| `BUNDLED_MODEL`, `BUNDLED_MODEL_NLOGOX`, `bundled_model` | the bundled model |

