.PHONY: check-name-param all

# Main target to build everything
all: check-name-param $(NAME)/graph_code.py

# Make 'all' the default target
.DEFAULT_GOAL := all

check-name-param:
ifndef NAME
	$(error NAME is not set. Usage: make NAME=something)
endif

# State specification depends on the input text file
$(NAME)/state-spec.md: $(NAME).txt
	@if [ ! -f $(NAME).txt ]; then \
		echo "Error: $(NAME).txt does not exist"; \
		exit 1; \
	fi
	@mkdir -p $(NAME)
	@if [ ! -f $(NAME)/llm_cache.py ]; then \
		cp llm_cache.py $(NAME)/; \
	fi
	@if [ ! -f $(NAME)/human_input.py ]; then \
		cp human_input.py $(NAME)/; \
	fi
	python mk_state_spec.py $(NAME).txt

# State code depends on state specification
$(NAME)/state_code.py: $(NAME)/state-spec.md
	python mk_state_code.py $(NAME).txt

# Node specification depends on state code
$(NAME)/node-spec.md: $(NAME)/state_code.py
	python mk_node_spec.py $(NAME).txt

# Node code depends on node specification
$(NAME)/node_code.py: $(NAME)/node-spec.md
	python mk_node_code.py $(NAME).txt

# Graph code depends on node code
$(NAME)/graph_code.py: $(NAME)/node_code.py
	python mk_graph_code.py $(NAME).txt

# Clean target to remove generated files
.PHONY: clean
clean: check-name-param
	rm -f $(NAME)/state-spec.md
	rm -f $(NAME)/state_code.py
	rm -f $(NAME)/node-spec.md
	rm -f $(NAME)/node_code.py
	rm -f $(NAME)/graph_code.py
